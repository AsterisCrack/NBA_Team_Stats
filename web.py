from bs4 import BeautifulSoup as bs
import requests
import pandas as pd

def extract():
    page = 'https://www.sportytrader.es/pronosticos/baloncesto/usa/nba-306'
    pageTree = requests.get(page)
    Soup = bs(pageTree.content, 'html.parser')
    # print(Soup.prettify())
    #New df
    df = pd.DataFrame(columns=['Home', 'Away', 'Prediction', 'Date'])
    scores = Soup.find_all('div', class_='flex flex-col xl:flex-row justify-center items-center border-2 border-primary-grayborder rounded-lg p-2 my-4')
    for score in scores:
        teams = score.find_all('div', class_='w-1/2 text-center break-word p-1 dark:text-white')
        home = teams[0].text
        away = teams[1].text
        #cleaning
        home = home.strip()
        away = away.strip()
        Prediction = score.find('span', class_='flex justify-center items-center h-7 w-6 rounded-md font-semibold bg-primary-green text-white mx-1').text
        if Prediction == '1':
            Prediction = home
        elif Prediction == '2':
            Prediction = away
        else:
            Prediction = 'DRAW'
        date = score.find('span', class_="text-xs dark:text-white").text
        df = pd.concat([pd.DataFrame({'Home': home, 'Away': away, 'Prediction': Prediction, 'Date':date}, index=[0]), df], ignore_index=True)
    return df

def transform(df, team):
    #date to datetime
    meses = ['ene.', 'feb.', 'mar.', 'abr.', 'may.', 'jun.', 'jul.', 'ago.', 'sep.', 'oct.', 'nov.', 'dic.']
    for i in range(len(df)):
        for j in range(len(meses)):
            if meses[j] in df['Date'][i]:
                df['Date'][i] = df['Date'][i].replace(meses[j], str(j+1))
                break
    df['Date'] = pd.to_datetime(df['Date'])

    #Search for team in either home or away
    df = df[(df['Home'] == team) | (df['Away'] == team)]
    #Sort by date
    df = df.sort_values(by='Date')
    return df

def load(df, team):
    prediction = ''
    if len(df) > 0:
        if df['Prediction'].iat[0] == team:
            print('The model predicts that', team, 'will win', df['Date'].iat[0])
            prediction = 'win'
        elif df['Prediction'].iat[0] == 'DRAW':
            print('The model predicts that', team, 'will draw', df['Date'].iat[0])
            prediction = 'draw'
        else:
            print('The model predicts that', team, 'will lose', df['Date'].iat[0])
            prediction = 'lose'
    else:
        print('No predictions for', team)
        prediction = None
    return prediction


