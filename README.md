## Inspiration
1) There are many different things that flights are dependent on and most of them are being collected manually. 
2) We think that  airline company is about flights. Therefor, all information that we have should be related to the flights.
 
## What it does
Our system automatically scans twitter, facebook, labour unions websites, then groups all this information based on its place, time and type (attack, strike, weather), and, represents all this knowledges in the dashboard. 
And, finally, analyses which exact flights are influenced by particular event and then shows it

## How we built it
We decided to split our work into several parts:
1) Scanning twitter ( and other sources but not today :) ) and looking for tweets (we call them *Mention* that may contain interesting information, e.g. terrorist attack, strike, weather condition, etc <br>
2) Extract from the tweets information about city, country and classify tweet itself (strike, terrorist attack, etc). Try to get the coordinates of the place <br>
3) There could be many tweets about the same event. During this step we group them and create *Event* entity. 
4)  Get weather information from openweathermap.org <br>
5) Analyse on which flights our events influence. For this reason we check whether we have flights from or to particular airports where event happened. <br>
6) Create a simple frontend to show that it works. We have 2 main pages:
- page with event, its type, how many flights are influenced 
- page with flights, where in we can see information about following flights, their status and events, connected to this flights. We think that that it is very important to know this information in order to make a decision.

## Challenges we ran into
- openweathermap.org limits us to use their API
- tweeter limits us to use their API
- difficult to extract information about relation between tweets and airport
- grouping *Mentions* into *Events* (how to know that 2 tweets is about exactly the same thing)

## Accomplishments that we're proud of
- we **do** extract information about relation between tweets and airport
- we **do** grouping *Mentions* into *Events* 

## What we learned
- what is airline company about
- some high-level understanding about what is under the hood

## What's next for Monitoring system for Finnair
- add integration with VAACs services
- add integration with Labour Unions websites and groups in order to get information about strikes
- for every event offer a solution and calculate it cost 
