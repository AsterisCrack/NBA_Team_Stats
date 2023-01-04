
#Import all necessary libraries
import json
import requests
import pandas as pd
import web
from fpdf import FPDF
import matplotlib.pyplot as plt
import os
import seaborn as sns
import datetime
import calendar

#Function to get data from API
def extract(Key):
    #First we get all the teams data
    endpoint = 'https://api.sportsdata.io/v3/nba/scores/json/AllTeams'
    headers = {'Ocp-Apim-Subscription-Key': Key}
    response = requests.get(endpoint, headers=headers)
    data = json.loads(response.text)
    #Now we need to know which team to use
    #We ask the user
    #The user might input the city, the team name or both
    #I create a dictionary with all the possible inputs
    teams = {}
    for team in data:
        teams[team['Key']] = [team['Name'].upper(), team['Key'].upper(), team['City'].upper(), team['City'].upper() + " " + team['Name'].upper()]
    #Now we ask the user until the input is valid
    ok = False
    while not ok:
        team = input('Enter your team: ').upper()
        for key in teams.keys():
            if team in teams[key]:
                team = key
                ok = True
                break
        if not ok:
            print('Team not found')
    #Now we have the team, extract just its data
    teams[team][0] = teams[team][0][0]+teams[team][0][1:].lower()
    my_team_data = {}
    for single_team in data:
        if single_team['Name'] == teams[team][0]:
            my_team_data = single_team

    data_team = {}
    for single_team in data:
        if single_team['Name'] == teams[team][0]:
            data_team = single_team
    team_id = data_team['TeamID']
    team_short = data_team['Key']
    
    #Team stats data
    endpoint = f'https://api.sportsdata.io/v3/nba/scores/json/TeamGameStatsBySeason/2023/{team_id}/all'
    response = requests.get(endpoint, headers=headers)
    team_season = json.loads(response.text)
    
    #All teams stats data
    endpoint = 'https://api.sportsdata.io/v3/nba/scores/json/Standings/2023'
    response= requests.get(endpoint, headers=headers)
    all_average = json.loads(response.text)

    #Player stats data
    endpoint = f'https://api.sportsdata.io/v3/nba/stats/json/PlayerSeasonStatsByTeam/2023/{team_short}'
    response = requests.get(endpoint, headers=headers)
    player_season = json.loads(response.text)

    #Game Schedules
    endpoint = f'https://api.sportsdata.io/v3/nba/scores/json/Games/2023'
    response = requests.get(endpoint, headers=headers)
    game_schedules = json.loads(response.text)

    return team_season, all_average, player_season, my_team_data, game_schedules

#Function to clean and transform data
def transform(team_season, all_average, player_season, game_schedules):
    #Make a df out of the team season stats
    team_season = pd.DataFrame(team_season)

    #Make a df out of the all teams average stats
    all_average = pd.DataFrame(all_average)
    #order by conference and conference rank
    #wins is int
    all_average['Wins'] = all_average['Wins'].astype(int)
    all_average = all_average.sort_values(by=['Conference', 'Wins'], ascending=[True, False])
    #reset index
    all_average = all_average.reset_index(drop=True)
    #Create position column
    all_average['Position'] = 1
    #When the conference changes, reset the position, there are 2 separate legues and hence rankings
    for i in range(len(all_average)):
        if i == 0:
            continue
        if all_average.loc[i]['Conference'] != all_average.loc[i-1]['Conference']:
            all_average.loc[i, 'Position'] = 1
        else:
            all_average.loc[i, 'Position'] = all_average.loc[i-1]['Position'] + 1


    #Make a df out of the player season stats
    player_season = pd.DataFrame(player_season)
    #order by points
    player_season = player_season.sort_values(by=['Points'], ascending=False)
    #reset index
    player_season = player_season.reset_index(drop=True)

    #Make a df out of the game schedules
    game_schedules = pd.DataFrame(game_schedules)
    #order by date
    game_schedules['Day'] = pd.to_datetime(game_schedules['Day'])
    game_schedules = game_schedules.sort_values(by=['Day'], ascending=True)
    #Take only the ones where HomeTeam or AwayTeam is the team
    game_schedules = game_schedules[(game_schedules['HomeTeam'] == team_season["Team"].iat[0]) | (game_schedules['AwayTeam'] == team_season["Team"].iat[0])]
    #reset index
    game_schedules = game_schedules.reset_index(drop=True)

    #Now we need to add the result of the game if it has already been played
    df_aux = team_season[['Day', 'Wins']].copy()
    df_aux = df_aux.sort_values(by='Day', ascending=True)
    df_aux = df_aux.reset_index(drop=True)
    df_aux['Day'] = pd.to_datetime(df_aux['Day'])
    game_schedules = game_schedules[['Day', 'HomeTeam', 'AwayTeam']]
    #merge the two dataframes, if there is no match, it will be NaN
    game_schedules = pd.merge(game_schedules, df_aux, how='left', on='Day')
    #fill the NaN with the previous value
    game_schedules['Wins'].fillna(2, inplace=True)
    game_schedules = game_schedules.reset_index(drop=True)

    #Now we need to add some columns that will be useful to create the calendar
    game_schedules['month'] = pd.DatetimeIndex(game_schedules['Day']).month
    game_schedules['day'] = pd.DatetimeIndex(game_schedules['Day']).day
    game_schedules['year'] = pd.DatetimeIndex(game_schedules['Day']).year
    game_schedules['MonthYear'] = pd.to_datetime(game_schedules['Day']).dt.to_period('M')
    game_schedules['Wins'] = game_schedules['Wins'].astype(int)

    return team_season, all_average, player_season, game_schedules

#Modify pdf class to add page numbers in the footer
class FPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        pageN = str(self.page_no())
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, pageN, 0, align='C')

#Function to make a calendar
def make_calendar(df, pdf):
    #This function takes a dataframe with the game schedules and a pdf object and creates a calendar inside the pdf
    #First we need to get the months to display
    unique_months = df['MonthYear'].unique()
    months = []
    month_fillings = []
    #Now we create a python calendar object for each month and a same-dimensional list to fill with the game results
    for i in range(len(unique_months)):
        #Create the calendar for the month
        month_fillings.append([])
        cal = calendar.monthcalendar(unique_months[i].year, unique_months[i].month)
        months.append(cal)
        #Fill in the results for each day
        for j in range(len(cal)):
            month_fillings[i].append([])
            for k in range(len(cal[j])):
                #search for this day in the dataframe
                if cal[j][k] != 0:
                    df_day = df.loc[(df['month'] == unique_months[i].month) & (df['day'] == cal[j][k]) & (df['year'] == unique_months[i].year)]
                    if df_day.empty:
                        #The date must be white since it is not a game day
                        month_fillings[i][j].append(3)
                    else:
                        month_fillings[i][j].append(df_day['Wins'].values[0])
                else:
                    #The date does not exist so it wont be displayed
                    month_fillings[i][j].append(4)
    pdf.ln(10)
    #Headers for the months and days of the week
    month_names = ["October 2022", "November 2022", "December 2022","January 2023", "February 2023", "March 2023", "April 2023"]
    week_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    #Color values
    red = (255, 40, 54)
    green = (163, 201, 38)
    blue = (25, 130, 196)
    #Pdf configurations for centering the calendar
    cal_width = 8*7*3 + 8*2
    prev_margin = pdf.l_margin
    pdf.set_left_margin(pdf.w/2 - cal_width/2)

    #The structure is 3 rows of 3 months each. The last row only has 1 month and must be centered
    #Each month has the month headers and the days of the week headers
    #Each month has 6 rows of 7 days each
    for row in range(3):
        #Print headers for each month
        for i in range(3):
            pdf.set_font("helvetica", size=10, style="B")
            if row == 2: # fix to center the last month
                pdf.cell(8*8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
            if row == 2 and i == 1:
                break
            pdf.cell(8*7, 8, month_names[i+row*3], 0, align="C", new_x="RIGHT", new_y="TOP")
            pdf.cell(8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
        pdf.ln(5)
        #Print headers for each day of the week
        for i in range(3):
            pdf.set_font("helvetica", size=10, style="")
            if row == 2: # fix to center the last month
                pdf.cell(8*8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
            if row == 2 and i == 1:
                break
            for j in range(7):
                pdf.cell(8, 8, week_names[j], 0, align="C", new_x="RIGHT", new_y="TOP")
            pdf.cell(8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
        pdf.ln(8)

        #For every month, print the 6 weeks
        for i in range(6): #6 rows corresponding to 6 weeks
            if row == 2: #If it is not the last month, which is alone
                pdf.cell(8*8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
            for j in range(3): #3 months
                for k in range(7): #7 days of the week
                    #Make the text to be printed
                    try:
                        text = str(months[j+row*3][i][k])
                    except:
                        text = "0"
                        if row == 2:
                            break
                    if text == "0":
                        text = "  "
                    if len(text) == 1: #Add a space to center the text, all numbers are 2 digits
                        text = " " + text
                    #Make the color to be printed for each cell, same thing as the text
                    try:
                        filling = month_fillings[j+row*3][i][k]
                    except:
                        filling = 4
                    if filling == 0:
                        pdf.set_fill_color(*red)
                    elif filling == 1:
                        pdf.set_fill_color(*green)
                    elif filling == 2:
                        pdf.set_fill_color(*blue)
                    elif filling == 3 or filling == 4:
                        pdf.set_fill_color(255, 255, 255)
                    print_border = 0 if filling == 4 else 1
                    #Print the cell
                    pdf.cell(8, 8, text, print_border, align="C", fill=True, new_x="RIGHT", new_y="TOP")
                pdf.cell(8, 8, " ", 0, align="C", new_x="RIGHT", new_y="TOP")
            pdf.ln(8)
    
    #Print the legend
    pdf.set_left_margin((pdf.w-129)//2)
    pdf.set_font("helvetica", size=10, style="")
    pdf.cell(25,10, "Game lost", 0, align="C", new_x="RIGHT", new_y="TOP")
    pdf.set_fill_color(*red)
    pdf.cell(8, 8, " ", 1, align="C", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.cell(10,10, "", 0, align="C", new_x="RIGHT", new_y="TOP")
    pdf.cell(25,10, "Game won", 0, align="C", new_x="RIGHT", new_y="TOP")
    pdf.set_fill_color(*green)
    pdf.cell(8, 8, " ", 1, align="C", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.cell(10,10, "", 0, align="C", new_x="RIGHT", new_y="TOP")
    pdf.cell(35,10, "Game scheduled", 0, align="C", new_x="RIGHT", new_y="TOP")
    pdf.set_fill_color(*blue)
    pdf.cell(8, 8, " ", 1, align="C", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.set_left_margin(prev_margin)               
    pdf.ln(10) 

def load(team_season, all_average, player_season, prediction, my_team_data, game_schedules):
    #Function to create a pdf output file with the season stats of the team
    #Create folder to store the graphs
    if not os.path.exists('aux_folder'):
        os.makedirs('aux_folder')

    #Set the styling, different for every team
    logo = my_team_data['WikipediaLogoUrl']
    color1HEX = my_team_data['PrimaryColor']
    color2HEX = my_team_data['SecondaryColor']
    #All colors from hex to rgb
    def hex2rgb(hex):
        hex = hex.lstrip('#')
        r = int(hex[0:2], 16)
        g = int(hex[2:4], 16)
        b = int(hex[4:6], 16)
        return r, g, b
    color1 = hex2rgb(color1HEX)
    color2 = hex2rgb(color2HEX)
    #Download logo
    with open(f'aux_folder/{team_season.loc[0]["Name"]}.svg', 'wb') as f:
        f.write(requests.get(logo).content)
    logo = f'aux_folder/{team_season.loc[0]["Name"]}.svg'

    #Using fpdf2 since it can load svg images
    pdf = FPDF()
    #The first page includes the title, logo and conference rankings and stats
    pdf.add_page()
    page_width = pdf.w - 2*pdf.l_margin
    pdf.set_font('helvetica', 'B', 20)
    pdf.cell(page_width, 10, f'{team_season.loc[0]["Name"]}', align='C')
    pdf.ln(7)
    pdf.set_font('helvetica', '', 12)
    #The data changes dayly, so the current date it is printed in the pdf
    today = datetime.datetime.now()
    txt = f'{today.strftime("%d/%m/%Y")}'
    pdf.cell(page_width, 10, txt, align='C')

    #Insert logo
    pdf.image(logo, x=page_width//2-5, y=30, w=30)

    #Get data to show team ranking in the conference
    conference = all_average.loc[all_average['Key'] == team_season.loc[0]['Team']]['Conference'].values[0]
    division = all_average.loc[all_average['Key'] == team_season.loc[0]['Team']]['Division'].values[0]
    position = all_average.loc[all_average['Key'] == team_season.loc[0]['Team']]['Position'].values[0]
    txt = f'{conference} conference, {division} division, position {position} in conference ranking'
    pdf.ln(60)
    pdf.cell(page_width, 10, txt, align='C')
    
    #Creeate a function to make tables
    #We will need a couple of them
    def print_table(columns, data):
        pdf.ln(10)
        pdf.set_font('helvetica', 'B', 10)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(.3)
        #Config to center the table
        table_witdh = 50 + 20*(len(columns)-2)
        prev_margin = pdf.l_margin
        pdf.set_left_margin(page_width//2-table_witdh//2)
        #Print the column names
        for i in range(len(columns)):
            if i == 0:
                pdf.cell(50, 10, columns[i], 1, align='C', new_x="RIGHT", new_y="TOP")
            else:
                pdf.cell(20, 10, columns[i], 1, align='C', new_x="RIGHT", new_y="TOP")
        pdf.set_font('helvetica', '', 10)
        pdf.ln(10)
        #Print the data
        for i in range(len(data)):
            if data[i][0] == team_season.loc[0]['Name']:
                pdf.set_font('helvetica', 'B', 10)
            else:
                pdf.set_font('helvetica', '', 10)
            try:
                pdf.cell(50, 10, data[i][0], 1, align='C', new_x="RIGHT", new_y="TOP")
            except:
                pdf.cell(50, 10, data[i][0].encode().decode('ascii', 'ignore'), 1, align='C', new_x="RIGHT", new_y="TOP")
            for j in range(1, len(data[i])):
                pdf.cell(20, 10, str(data[i][j]), 1, align='C', new_x="RIGHT", new_y="TOP")
            pdf.ln(10)
        pdf.set_left_margin(prev_margin)

    #Print the table with the conference rankings
    columns = ['Team', 'Pos', 'Wins', 'Losses', 'Win %']
    data = all_average[all_average['Conference'] == conference].copy()
    #merge city and name
    data['Name'] = data['City'] + " " + data['Name']
    data = data[['Name', 'Position', 'Wins', 'Losses', 'Percentage']].values
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(page_width, 10, 'Conference ranking', align='C')
    print_table(columns, data)

    #Function to create custom data graphs
    #It uses the teams colors and can highlight a bar
    def bar_graph(datos, titulo, x_lab, y_lab, save, destacar=None):
        #SNS bar graph where color1 is the color of the highlighted bar and color2 is the color of the rest
        #Bars must have a black border since the color can be white for some teams
        #It also has a custom title, x and y labels
        #Create color map
        colors = [f'#{color2HEX}']*len(datos)
        if destacar:
            colors[destacar] = f'#{color1HEX}'
        #X is the values of the first column of the dataframe
        #Y is the values of the second column of the dataframe
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x=datos.iloc[:,0], y=datos.iloc[:,1], palette=colors, ax=ax, linewidth=1, edgecolor='black')
        ax.set_title(titulo)
        ax.set_xlabel(x_lab)
        ax.set_ylabel(y_lab)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=20, horizontalalignment='right')
        #The highlighted bar has a value on top of it
        if destacar:
            bar = ax.patches[destacar]
            # Get the bar's x and y coordinates
            x = bar.get_x()
            y = bar.get_height()
            # Use these coordinates to annotate the bar with the total value
            ax.text(x + bar.get_width()/2., y+1, f"{y:.2f}", ha="center")

        if y_lab != 'Win %':
            plt.tight_layout()
        plt.savefig(save)
        plt.close()

    #Make a graph of the team's points per game average
    df_aux = all_average[all_average['Conference'] == conference][['Name', 'PointsPerGameFor', 'PointsPerGameAgainst', 'Key']].copy()
    #Points per game for is for + against / 2
    df_aux['PointsPerGameFor'] = (df_aux['PointsPerGameFor'] + df_aux['PointsPerGameAgainst'])/2
    df_aux = df_aux.sort_values(by='PointsPerGameFor', ascending=False)
    df_aux = df_aux.reset_index(drop=True)
    team_pos = df_aux[df_aux['Key'] == team_season.loc[0]['Team']].index[0]
    df_aux = df_aux[['Name', 'PointsPerGameFor']]
    img1 = 'aux_folder/points_per_game.png'
    bar_graph(df_aux, 'Points per game', None, 'PPG', img1, team_pos)

    #Make a graph of the team's win percentage
    df_aux = all_average[all_average['Conference'] == conference][['Name', 'Percentage', 'Key']].copy()
    df_aux = df_aux.sort_values(by='Percentage', ascending=False)
    df_aux = df_aux.reset_index(drop=True)
    team_pos = df_aux[df_aux['Key'] == team_season.loc[0]['Team']].index[0]
    df_aux = df_aux[['Name', 'Percentage']]
    img2 = 'aux_folder/win_percentage.png'
    bar_graph(df_aux, 'Win percentage', None, 'Win %', img2, team_pos)
    
    #New page to place the graphs
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(page_width, 10, 'Team stats', align='C')
    pdf.ln(20)
    pdf.image(img1, x=20, y=pdf.get_y(), w=page_width-20)
    pdf.ln(100)
    pdf.image(img2, x=20, y=pdf.get_y(), w=page_width-20)

    #New page for the player stats
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(page_width, 10, 'Team Players', align='C')
    pdf.ln(10)
    #Table of players
    columns = ['Name', 'Position', 'Games', 'Minutes', 'Points', 'Rebounds', 'Assists', 'Steals', 'Blocks']
    data = player_season[player_season['Team'] == team_season.loc[0]['Team']].copy()
    data = data[['Name', 'Position', 'Games', 'Minutes', 'Points', 'Rebounds', 'Assists', 'Steals', 'BlockedShots']].values
    print_table(columns, data)

    pdf.add_page()
    #Graph of minutes played
    df_aux = player_season[player_season['Team'] == team_season.loc[0]['Team']].copy()
    df_aux = df_aux.sort_values(by='Minutes', ascending=False)
    df_aux = df_aux.reset_index(drop=True)
    df_aux = df_aux[['Name', 'Minutes']]
    img3 = 'aux_folder/minutes_played.png'
    bar_graph(df_aux, 'Minutes played', 'Player', 'Minutes', img3)

    #Graph of points
    df_aux = player_season[player_season['Team'] == team_season.loc[0]['Team']].copy()
    df_aux = df_aux.sort_values(by='Points', ascending=False)
    df_aux = df_aux.reset_index(drop=True)
    df_aux = df_aux[['Name', 'Points']]
    img4 = 'aux_folder/points.png'
    bar_graph(df_aux, 'Points', 'Player', 'Points', img4)

    #Graph of blocks
    df_aux = player_season[player_season['Team'] == team_season.loc[0]['Team']].copy()
    df_aux = df_aux.sort_values(by='BlockedShots', ascending=False)
    df_aux = df_aux.reset_index(drop=True)
    df_aux = df_aux[['Name', 'BlockedShots']]
    img5 = 'aux_folder/blocks.png'
    bar_graph(df_aux, 'Blocks', 'Player', 'Blocks', img5)

    #Place images
    pdf.image(img3, x=20, y=pdf.get_y(), w=page_width-20)
    pdf.ln(90)
    pdf.image(img4, x=20, y=pdf.get_y(), w=page_width-20)
    pdf.ln(90)
    pdf.image(img5, x=20, y=pdf.get_y(), w=page_width-20)

    #New page for the calendar
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(page_width, 10, 'Game Calendar', align='C')
    pdf.ln(10)
    #Print the calendar
    make_calendar(game_schedules, pdf)
    pdf.ln(20)
    #Print predictions
    pdf.set_font('helvetica', 'B', 12)
    if prediction:
        text = f'The prediction for next game is that {team_season.loc[0]["Name"]} will {prediction}'
    else:
        text = f'The prediction for next game is not available yet'
    pdf.multi_cell(page_width, 10, text, align='C')
    #Save and close pdf
    #if folder out does not exist, create it
    if not os.path.exists('out'):
        os.makedirs('out')
    pdf.output('out/report.pdf')
    
    #delete aux folder and its contents
    for i in os.listdir('aux_folder'):
        os.remove(f'aux_folder/{i}')
    os.rmdir('aux_folder')

if __name__ == '__main__':
    #Get key from config.txt
    with open('config.txt', 'r') as f:
        Key = f.readline()
    Key=Key.split('=')[1]
    Key=Key.strip()
    #If the key is wrong, tell the user and exit
    try:
        team_season, all_average, player_season, my_team_data, game_schedules = extract(Key)
    except:
        print('Error extracting, check that your key is correct')
        exit()
        
    #Execute both ETL at the same time
    predictions = web.extract()
    team_season, all_average, player_season, game_schedules = transform(team_season, all_average, player_season, game_schedules)
    df = web.transform(predictions, team_season["Name"].iat[0])
    prediction = web.load(df, team_season["Name"].iat[0])
    load(team_season, all_average, player_season, prediction, my_team_data, game_schedules)
