import requests
import pandas as pd
import arrow
import datetime
import os
 
def get_yahoo_quote(symbol='SBIN', data_range='90d', data_interval='1h'):
    res = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.BO?range={data_range}&interval={data_interval}'.format(**locals()))
    data = res.json()
    body = data['chart']['result'][0]    
    dt = datetime.datetime
    dt = pd.Series(map(lambda x: arrow.get(x).to('Asia/Calcutta').datetime.replace(tzinfo=None), body['timestamp']), name='Datetime')
    df = pd.DataFrame(body['indicators']['quote'][0], index=dt)
    dg = pd.DataFrame(body['timestamp'])    
    df.dropna(inplace=True)     #removing NaN rows
    df = df[(df.open != 0) & (df.high != 0) & (df.low != 0) & (df.close != 0)]
    df = df.reset_index()
    df[['date', 'time']]=df['Datetime'].astype(str).str.split(' ', expand=True)
    df = df.loc[:, ('date', 'time', 'open', 'high', 'low', 'close', 'volume')]
     
    return df
