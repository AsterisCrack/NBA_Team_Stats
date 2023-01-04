# NBA_Team_Stats
A python program that uses an API to create a stats report and predictions for any NBA team.

## Project functionalities
This python program creates a pdf document with some interesting stats for any NBA team in the 2023 season. It uses https://sportsdata.io/ API to get all the stats.
The pdf is completely customized for the team you selected by using its logo and colors.
Also, it reads https://www.solobasket.com/apuestas-deportivas/pronosticos-nba/ website to obtain predictions for the next game.
The pdf report includes:
- General stats and league position for all teams in the conference.
- Graphs to represent some of these stats.
- Stats of the team's players.
- Graphs to represent some of the player stats.
- A calendar for the played and scheduled games.
- A prediction (if available) for next game.
- 
## Tutorial
To execute this project, first download all necessary libraries by running: 
$pip3 install -r requirements.txt
When the libraries finished downloading, modify the "config.txt" folder to insert your API key. To get a key you will need to register in https://sportsdata.io/ first. 
Then, just substitute the placeholder "key" with your own key (without ", ' or spaces, make sure your key is correct!)
Finally, just ruun the program by running the following command in your console:
$python getdata.py

## Docker
Also, you can execute the program with a docker container. To buid the container firsr run:
$docker build -t nba_stats .
Then, when the container is built, just run:
$docker run -it -v /HostOut:/out nba_stats
MAke sure you first have a folder named "HostOut" in your work directory.
