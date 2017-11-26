import twitter
from tqdm import tqdm
from copy import copy
from datetime import datetime
from time import strptime
import pandas as pd
import nltk
import numpy as np
from enum import Enum

EVENT_TYPE = Enum('EVENT_TYPE', 'TERRORIST_ATTACK LABOUR_STRIKE')

class Mention():
    datetime_happened = None
    datetime_reported = None
    longitude = None
    lattitude = None
    type = None
    # Please use standard system: SVO, SCO, TSE
    airport_id = None
    city_name = None
    country_name = None
    raw_description = None
    
    @classmethod
    def gen_explicitly(cls, type, airport_id, datetime_reported, datetime_happened=None, lattitude=None, longitude=None, city_name=None, country_name=None, raw_description=None):
        m = Mention()
        m.datetime_happened = datetime_happened
        m.datetime_reported = datetime_reported
        m.longitude = longitude
        m.lattitude = lattitude
        m.type = type
        m.airport_id = airport_id
        m.city_name = None if city_name is None else city_name.lower()
        m.country_name = None if country_name is None else country_name.lower()
        m.raw_description = None
        return m
        
    @classmethod
    def gen_from_twitter(cls,status_dict,cities_set,icao_set,iata_set):
        m = Mention()       
        
        m.datetime_reported = pd.Timestamp.strptime(status_dict['created_at'],
                                               '%a %b %d %H:%M:%S +0000 %Y').timestamp()
        if 'utc_offset' in status_dict['user']:
            m.datetime_reported += status_dict['user']['utc_offset']
        
        if 'location' in status_dict['user']:
            m.city_name = status_dict['user']['location'].split(',')[0].lower()
        if 'place' in status_dict:
            if status_dict['place']['place_type'] == 'city':
                if m.city_name:
                    pass
                    #print('overwriting city {} with {}'.format(m.city_name,status_dict['place']['name']))
                m.city_name = status_dict['place']['name'].lower()
                # m.country_name = status_dict['place']['full_name'].split(',')[1].strip() в презе не нужно
            if status_dict['place']['place_type'] == 'country':
                pass # не нужно для презы
            if 'bounding_box' in status_dict['place']:
                m.longitude = (status_dict['place']['bounding_box']['coordinates'][0][2][0]+ \
                                  status_dict['place']['bounding_box']['coordinates'][0][3][0])/2.0
                m.lattitude = (status_dict['place']['bounding_box']['coordinates'][0][2][1]+ \
                                  status_dict['place']['bounding_box']['coordinates'][0][3][1])/2.0 # ??
        m.raw_description = status_dict['text']
        tokenized_text_set = set(nltk.word_tokenize(m.raw_description.lower()))
        cities_in_text = list(tokenized_text_set & cities_set)
        if cities_in_text:
            m.city_name = cities_in_text[0].lower()
        airports_in_text = list( tokenized_text_set & (icao_set | iata_set) ) 
        if airports_in_text:
            m.airport_id = airports_in_text[0]
        m.type = status_dict['type']
        m.id = status_dict['id']
        return m
   
    def print_self(self):
        """" Obsolete function. Better use __repr__ instead """
        print("datetime_happened {}".format(self.datetime_happened))
        print("datetime_reported {}".format(self.datetime_reported))
        print("longitude         {}".format(self.longitude))
        print("lattitude         {}".format(self.lattitude))
        print("type              {}".format(self.type))
        print("airport_id        {}".format(self.airport_id))
        print("city_name         {}".format(self.city_name))
        print("country_name      {}".format(self.country_name))
        print("raw_description   {}".format(self.raw_description))
        
    def __repr__(self):        
        res = "\n".join(["datetime_happened {}".format(self.datetime_happened),
        "datetime_reported {}".format(self.datetime_reported),
        "longitude         {}".format(self.longitude),
        "lattitude         {}".format(self.lattitude),
        "type              {}".format(self.type),
        "airport_id        {}".format(self.airport_id),
        "city_name         {}".format(self.city_name),
        "country_name      {}".format(self.country_name),
        "raw_description   {}".format(self.raw_description),
        "tweet it          {}".format(self.id)])
        return res

class Event(Mention):
    mentions = []
    flights_affected = []
    
    def __init__(self, m:Mention):
        self.datetime_happened = m.datetime_happened
        self.datetime_reported = m.datetime_reported
        self.longitude = m.longitude
        self.lattitude = m.lattitude
        self.type = m.type
        self.airport_id = m.airport_id
        self.city_name = None if m.city_name is None else m.city_name.lower()
        self.country_name = None if m.country_name is None else m.country_name.lower()
        self.raw_description = None
        #super().__init__(m.type, m.airport_id, m.datetime_reported, m.datetime_happened, m.lattitude, m.longitude, m.city_name, m.country_name, None)
        self.mentions.append(m)
        
    def __eq__(self, other):
        return (self.airport_id == other.airport_id 
                and self.datetime_happened == other.datetime_happened 
                and self.type == self.type)
    
    def get_confidence():
        pass