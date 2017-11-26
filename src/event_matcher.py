import pandas as pd
import os.path
import shelve
from math import sin, cos, sqrt, atan2, radians

class EventCollection:
    events = []
    last_event_id = None
    def __init__(self):
        
        self.airport_db = pd.read_csv('../data/airports.csv')

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

        
        if os.path.isfile('../data/events.idx'):
            with shelve.open('../data/events.idx') as db:
                self.last_event_id = db['last_event_id']
                self.events = db['events']

    def save(self):
        with shelve.open('../data/events.idx', writeback=True) as db:
            db['last_event_id'] = self.last_event_id
            db['events'] = self.events
            db.sync()
           
    def add_event(self, mention:Mention):
        if mention.longitude is None and mention.lattitude is None and mention.airport_id is None and mention.city_name is None and mention.country_name is None:
            print("Not enough data in Mention! Not considering this.")
            return
        
        mention = fill_missing_data(mention)
        if len(self.events) == 0:
            print("Adding a new event_")
            self.events.append(Event(mention))
            self.last_event_id = mention.id
            self.save()
            return
        
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
            self.events.append(Event(mention))
            self.last_event_id = mention.id
            self.save()
            return
        if len(similar_events) == 1:
            print("Merging with one similar event")
            similar_events[0].mentions.append(mention)
            self.last_event_id = mention.id
            self.save()
            return
        
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
        self.save()
        
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