import twitter
from tqdm import tqdm
from copy import copy
from datetime import datetime
from time import strptime
import pandas as pd
import nltk
import numpy as np
from enum import Enum
import os.path
import shelve

from app.mention import EVENT_TYPE, Mention, Event


class TwitterParser():
    def __init__(self):
        self.api = twitter.Api(consumer_key='USctDCgnlL3bNRB6UuXn7d236',
                          consumer_secret='J2VViasvzh3joWrl8sHicoKLnHcjtWk9mM7O9wsieWyqy4W1PL',
                          access_token_key='782531360-ldm9KTYfSwyKXIq4Axh9Op6fDP0IarPCuIl6xzkh',
                          access_token_secret='vKDEmonUAxvL1M1YGvMXDL6OfNwvKgzTD9Se6qKsLRnjT')
        self.api.VerifyCredentials()
        self.airports_data = pd.read_csv('data/airports.csv')
        self.airports_data.city.fillna(value='')
        self.cities_set = set([str(i).lower() for i in self.airports_data['city'].values])
        self.icao_set = set(self.airports_data['icao'])
        self.iata_set = set(self.airports_data['iata'])
        #airports_data.head()
        self.key_words = ['terrorist attack', 'explosion in the airport','labour strike','union strike']
        self.key_words_last_ids = dict(zip(self.key_words,[None]*len(self.key_words)))
        print(self.key_words_last_ids)
        EVENT_TYPE = Enum('EVENT_TYPE', 'TERRORIST_ATTACK LABOUR_STRIKE')
        self.event_dict ={'terrorist attack':EVENT_TYPE.TERRORIST_ATTACK,
                         'explosion in the airport':EVENT_TYPE.TERRORIST_ATTACK,
                         'labour strike':EVENT_TYPE.LABOUR_STRIKE,
                         'union strike':EVENT_TYPE.LABOUR_STRIKE
                         }
        self.first_launch = True
        if os.path.isfile('data/events.idx'):
            with shelve.open('data/events.idx') as db:
                self.key_words_last_ids = db['key_words_last_ids']
                self.first_launch = False
        
    def save(self):
        with shelve.open('data/events.idx', writeback=True) as db:
            db['key_words_last_ids'] = self.key_words_last_ids
            db.sync()
            
    def parse_twitter(self):    
        all_res = []
        num_iterations = 5 # на практике это слишком много и не нужно
        #event_dict ={'terrorist attack':EVENT_TYPE.TERRORIST_ATTACK,'labour_strike':EVENT_TYPE.LABOUR_STRIKE}
        for key in self.key_words:
            print("collecting data for '{}' keyword".format(key))
            if self.first_launch:
                all_data = self.api.GetSearch(term=key,
                                              count=100,
                                              result_type='recent')
                self.first_launch = False
            else:
                all_data = self.api.GetSearch(term=key,
                                              count=100,
                                              result_type='recent',
                                              since_id=self.key_words_last_ids[key])
            if len(all_data) == 0:
                continue
            last_id = all_data[-1].AsDict()['id']
            for i in range(num_iterations): # заменить на 50
                all_data.extend(self.api.GetSearch(term=key,
                                                   count=100,
                                                   result_type='recent',
                                                   max_id=last_id-1,
                                                   since_id=self.key_words_last_ids[key]))
                last_id = all_data[-1].AsDict()['id']
            self.key_words_last_ids[key] = all_data[0].AsDict()['id']
            self.save()
            #all_res.append([])
            for tweet in all_data:
                if ('retweeted_status' not in tweet.AsDict().keys()) and ('quoted_status' not in tweet.AsDict().keys()):
                    dict_tweet = tweet.AsDict()
                    dict_tweet['type'] = self.event_dict[key]
                    all_res.append(Mention.gen_from_twitter(dict_tweet,self.cities_set,self.icao_set,self.iata_set))
            #print('{}/{} tweets are not retweets'.format(len(all_res[-1]),num_iterations*100))
        return all_res

def delete_last_statuses(num_to_delete):
    for stat_id in [status.AsDict()['id'] for status in api.GetUserTimeline(count=num_to_delete)]:
        api.DestroyStatus(stat_id)
def make_post(text):
    api.PostUpdate(text + '    randseed:'+ str(np.random.randint(1000)))

