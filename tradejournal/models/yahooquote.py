import requests
import pandas as pd
import arrow
import datetime
import os

YAHOO_SYMBOL_MAPPINGS={
    'NIFTY': '^NSEI',
    'BANKNIFTY' : '^NSEBANK',
    'CRUDEOIL' : 'CL=F',
    'NATURALGAS' : 'NG=F',
    'GOLD' : 'GC=F',
    'SILVER' : 'SI=F',
    'COPPER' : 'HG=F',
    #'ALUMINIUM' : 'ALI=F',
    'USDINR' : 'INR=X',
    'GBPINR' : 'GBPINR=X',
    'JPYINR' : 'JPYINR=X',
    'EURINR' : 'EURINR=X',
}

def get_yahoo_symbol(symbol):
    if symbol in YAHOO_SYMBOL_MAPPINGS.keys():
        return YAHOO_SYMBOL_MAPPINGS[symbol]
    return symbol+'.BO'
 
def get_yahoo_quote(symbol='RELIANCE', data_range='1d', data_interval='1h'):
    ysymbol = get_yahoo_symbol(symbol)
    res = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/{ysymbol}?range={data_range}&interval={data_interval}'.format(**locals()))
    data = res.json()
    body = data['chart']['result'][0]    
    dt = datetime.datetime
    dt = pd.Series([arrow.get(x).to('Asia/Calcutta').datetime.replace(tzinfo=None) for x in body['timestamp']], name='Datetime')
    df = pd.DataFrame(body['indicators']['quote'][0], index=dt)
    dg = pd.DataFrame(body['timestamp'])    
    df.dropna(inplace=True)     #removing NaN rows
    df=df.reset_index()
    df[['date', 'time']]=df['Datetime'].astype(str).str.split(' ', expand=True)
    df = df.loc[:, ('date', 'time', 'open', 'high', 'low', 'close', 'volume')]
    
    return df

def get_all_quotes(listname, data_range, data_interval, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    with open(listname) as fin:
        for symbol in fin.readlines():
            symbol = symbol.strip()
            try:
                data = get_quote_data(symbol, data_range, data_interval)
                data.to_csv(output_dir+'\\'+symbol+'.csv', float_format='%.2f', index=False)
            except KeyboardInterrupt: 
                raise
            except:
                print('Fetching %s failed'%symbol)

if __name__ == "__main__":
    path = os.path.join(os.path.expanduser(r'~\Documents'), 'NSEIntraday1h')
    get_all_quotes('fno.tls', '120d', '1h', path)
    #get_all_quotes('fno.tls', '60d', '15m', 'NSEIntraday15m')
    #data = get_quote_data()
    #print (data)
    #data.to_csv('temp.csv', float_format='%.2f', index=False)
