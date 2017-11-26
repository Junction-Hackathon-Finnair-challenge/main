import time
import pickle

from app import mention
from app.twitter_parser import TwitterParser
from app.flight_mapping import FlightControlSystem
#from app.event_matcher import EventCollection

parser = TwitterParser()
controlSystem = FlightControlSystem()
controlSystem.forecasts = pickle.load( open('data/forecasts.p', 'rb'))

while(True):
    mentions = parser.parse_twitter()
    for m in mentions:
        e = controlSystem.add_mention(mention)
        if e is not None:
            # compute affected flights
            controlSystem.add_event(e)
            controlSystem.save()
    time.sleep(3*60)