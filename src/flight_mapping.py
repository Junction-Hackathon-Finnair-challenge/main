import pandas as pd
from pandas._libs.tslib import Timestamp, Timedelta
import numpy as np
import pyowm

from app import mention

#flights = pd.read_csv('Flights_schedule.csv', index_col = 'Id')
#flights['Departure datatime'] = pd.to_datetime(flights['Departure datatime'])
#flights['Arrival datatime'] = pd.to_datetime(flights['Arrival datatime'])
#owm = pyowm.OWM('fd7f55cd600a4e84dc1cb6797915f3ee')


class FlightControlSystem():
    schedule = None
    event_list = []
    port_list = []
    forecasts = {}
    last_event_id = None
    
    def __init__(self, sourse='data/Flights_schedule.csv'):
        if os.path.isfile('data/events.idx'):
            with shelve.open('data/events.idx') as db:
                self.last_event_id = db['last_event_id']
                self.event_list = db['event_list']
                self.schedule = db['schedule']
                self.port_list = db['port_list']
                self.forecasts = db['forecast']
        else:
            self.event_list = []
            temp = pd.read_csv('data/Flights_schedule.csv')
            temp['Departure datatime'] = pd.to_datetime(temp['Departure datatime'])
            temp['Arrival datatime'] = pd.to_datetime(temp['Arrival datatime'])

            self.port_list = set(temp['Departure port'].values)
            self.port_list.update(set(temp['Arrival port'].values))

            self.schedule = self.actualizer(temp)

        
        self.airport_db = pd.read_csv('data/airports.csv')

        self.airport_db["city"] = self.airport_db["city"].str.lower()
        self.airport_db["country"] = self.airport_db["country"].str.lower()

        # How many cities have only one airport?
        self.airport_names = {a[0]:(str(a[1]['city']) + ' ' + str(a[1]['country'])) for a in self.airport_db.iterrows()}
        self.airport_names_rev = {self.airport_names[a]:a for a in self.airport_names.keys()}
        self.airport_freq =  pd.DataFrame(list(self.airport_names.values()), index=list(self.airport_names.keys()))[0].value_counts()
        self.one_airport_cities_i = [self.airport_names_rev[a] for a in self.airport_freq.keys() if self.airport_freq[a] == 1]

        # How many unique cities?
        self.airport_city_freq =  self.airport_db['city'].value_counts()
        self.city_one_airport_names = [a for a in self.airport_city_freq.keys() if self.airport_city_freq[a] == 1]

    def save(self):
        with shelve.open('data/events.idx', writeback=True) as db:
            db['last_event_id'] = self.last_event_id
            db['event_list'] = self.event_list
            db['schedule'] = self.schedule
            db['port_list'] = self.port_list
            db['forecast'] = self.forecasts
            db.sync()
            
    def add_mention(self, mention:Mention):
        if mention.longitude is None and mention.lattitude is None and mention.airport_id is None and mention.city_name is None and mention.country_name is None:
            print("Not enough data in Mention! Not considering this.")
            return None
        
        mention = fill_missing_data(mention)
        if len(self.event_list) == 0:
            print("Adding a new event_")
            #self.events.append(Event(mention))
            self.last_event_id = mention.id
            return Event(mention)
        
        # Merge with some event
        TIME_EPSILON_SECONDS = 24*60*60
        
        similar_events = list(filter(
            lambda e: e.type == mention.type and
                (((e.airport_id is not None and 
                   mention.airport_id is not None and 
                   e.airport_id == mention.airport_id) or 
                (e.city_name is not None and 
                 mention.city_name is not None and
                 e.country_name is not None and mention.country_name is not None and
                 e.city_name == mention.city_name and e.country_name == mention.country_name)) and 
                abs(e.datetime_happened - mention.datetime_happened) < TIME_EPSILON_SECONDS), self.events))
        print("Found %d similar events" % len(similar_events))
        
        if len(similar_events) == 0:
            print("Adding a new event")
            #self.events.append(Event(mention))
            self.last_event_id = mention.id
            #self.save()
            return Event(mention)
        if len(similar_events) == 1:
            print("Merging with one similar event")
            similar_events[0].mentions.append(mention)
            self.last_event_id = mention.id
            #self.save()
            return None
        
        # weight similar events
        weights = [0 for _ in range(len(similar_events))]
        for i in range(len(similar_events)):
            e = similar_events[i]
            w = 0
            if e.airport_id == mention.airport_id:
                w += 1
            if e.city_name == mention.city_name and e.country_name == mention.country_name:
                w += 0.5
            
            w += 1/(10*abs(e.datetime_happened - mention.datetime_happened))
            weights[i] = w
        max_w = max(weights)
        indexes = [i for i, x in enumerate(weights) if x == max_w]
        if len(indexes) > 1:
            print("Warning, there are %d similar events for merging, selecting the first one" % len(indexes))
        
        similar_events[indexes[0]].mentions.append(mention)
        self.last_event_id = mention.id
        similar_events[indexes[0]].datetime_happened = sum([m.datetime_happened for m in similar_events[indexes[0]].mentions]) / float(len(l))
        print("Merged")
        #self.save()
        return None
    
    def geo_to_airport(lat, lon):
        distance_epsilon = 10 # km
        lat = radians(lat)
        lon = radians(lon)
        for airport in self.airport_db.iterrows():
            airport = airport[1]
            lat2 = radians(airport['latitude'])
            lon2 = radians(airport['longitude'])
            dlon = lon2 - lon
            dlat = lat2 - lat
            a = sin(dlat / 2)**2 + cos(lat) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            # Approximate earth radius is 6373.0
            distance = 6373.0 * c
            if distance < distance_epsilon:
                return airport.iata
        return None

    def fill_missing_data(self, mention:Mention):
        if mention.datetime_happened is None:
            mention.datetime_happened = mention.datetime_reported
        if mention.airport_id is None:
            if mention.lattitude is not None and mention.longitude is not None:
                #Reverse geocodes
                mention.airport_id = self.geo_to_airport(mention.lattitude, mention.longitude)
            if mention.airport_id is None and mention.city_name is not None and mention.country_name is not None:
                if airport_names[mention.city_name + ' ' + mention.country_name] in one_airport_cities_i:
                    # One airport in the city
                    mention.airport_id = self.airport_db.loc[airport_names[mention.city_name + ' ' + mention.country_name]].iata

            if mention.airport_id is None and mention.city_name is not None and mention.city_name in city_one_airport_names:
                mention.airport_id = self.airport_db.loc[self.airport_db[self.airport_db['city'] == mention.city_name].index[0]].iata
                print(mention.airport_id)
        return mention
        
    def air2coords(name):
        lat = self.airport_db[self.airport_db['iata'] == name].latitude.values[0]
        long = self.airport_db[self.airport_db['iata'] == name].longitude.values[0]
        return float(lat), float(long)

    def place2air(city, country):
        return self.airport_db[self.airport_db['city'] == city][airport_db['country'] == country]['iata'].values

    def actualizer(self, sch, after_date = None):
        if after_date is None:
            after_date = Timestamp.today()
            
        return sch[sch['Arrival datatime'] > after_date]
    
    def add_event(self, event, time_area = '1 days'):
        if self.check_similars(event):
            return []
        
        if event.airport_id == None:
            if event.city_name == None or event.country_name == None:
                print('Incorrect event. Make it ok and try again')
                return []
            
            air_ids = place2air(event.city_name, event.country_name)
        else:
            air_ids = [event.airport_id]
            
        
        ids = []
        print(len(air_ids))
        print(air_ids)
        for air_id in air_ids:
            if air_id not in self.port_list:
                print('mimo')
                continue
                
            by_port_arriv = self.schedule[self.schedule['Arrival port'] == air_id].index
            by_port_dept = self.schedule[self.schedule['Departure port'] == air_id].index

            by_date_dept = self.schedule[self.schedule['Departure datatime'] - event.datetime_happened < time_area][event.datetime_happened  - self.schedule['Departure datatime']< time_area].index
            by_date_arriv = self.schedule[self.schedule['Arrival datatime'] - event.datetime_happened < time_area][event.datetime_happened  - self.schedule['Departure datatime']< time_area].index

            ids = np.concatenate((np.intersect1d(by_port_arriv, by_date_arriv),np.intersect1d(by_port_dept, by_date_dept)))

#             print('by port {}'.format(len(by_port_arriv) + len(by_port_dept)))
#             print('by date {}'.format(len(by_date_arriv) + len(by_date_dept)))
#             print(ids)

            event.flights_affected += ids.tolist()
        self.event_list.append(event)
        
        return ids
    
    def check_similars(self, event):
        if event in self.event_list:
            pass
            #do somethind..................
        else:
            return False
        
    
    def events_by_fid(self, fid):
        return [e for e in self.event_list if fid in e.flights_affected]
    
    def flights_by_event(self, ids):
        l = [e.flights_affected for e in self.event_list is e.id in ids]
        return sum(l, [])
    
    def create_event(self,port, time, type, value):
        e = Event(Mention(airport_id=port, 
                          type='snow', 
                          datetime_reported=Timestamp.today(), 
                          datetime_happened=time, 
                          raw_description=value))
        self.add_event(e, time_area='01:00:00')
        return e
        
    
    def data_request(self):
        for i, port in enumerate(self.port_list):
            if i % 50 == 9:
                time.sleep(60)
               
            coords = air2coords(port)
            self.forecasts[port] = owm.three_hours_forecast_at_coords(*coords)
            
        
    def weather_update(self):
        three_day_flights = self.schedule[self.schedule['Arrival datatime'] - Timestamp.today() < Timedelta('3 days')]
        three_day_flights = three_day_flights[three_day_flights['Departure datatime'] - Timestamp.today() > Timedelta('3:00:00')].index
        for i in three_day_flights:
#             print('%2d from %d, event_list: %d' %(i, len(three_day_flights), len(self.event_list)), end='\r')
            flight = self.schedule.loc[i]
            
            for stuff in ['Departure ', 'Arrival ']:

                forecast = self.forecasts[flight[stuff + 'port']]
                weather = forecast.get_weather_at(flight[stuff + 'datatime'])

                snow = weather.get_snow().get('3h', 0)
                if snow > 3: # Attention! Magic numbers!
                    e = self.create_event(flight[stuff + 'port'], flight[stuff + 'datatime'], 'snow', snow)
                    print('new snow event ',snow, ' ', len(e.flights_affected), ' ', e.datetime_happened)

                wind = weather.get_wind().get('speed', 0)
                if wind > 7: # Attention! Magic numbers!
                    e = self.create_event(flight[stuff + 'port'], flight[stuff + 'datatime'], 'strong wind', wind)
                    print('new wind event ',wind, ' ', len(e.flights_affected), ' ', e.datetime_happened)

                # to be continued .......


            
                
        
        
    