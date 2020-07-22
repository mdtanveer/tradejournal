import pandas as pd

def resample_quote_data(df, resample_tf='2H'):
    df['datetime'] = df.date + 'T' + df.time + '.0000Z'
    df.datetime = pd.to_datetime(df.datetime)
    df=df.set_index(df.datetime)
    df=df.drop(['date', 'time', 'datetime'], axis=1)

    dfs=df.tshift(1, freq='H')

    dfr=dfs.resample(resample_tf).agg({
        'open':'first',
        'high':'max',
        'low':'min',
        'close':'last',
        'volume':'sum'
    })
    dfr=dfr.dropna()
    dfr=dfr.tshift(-45, freq="T")
    dfr = dfr.reset_index()
    dfr['date'], dfr['time'] = zip(*dfr[['datetime']].apply(lambda r: (r.datetime.date(), r.datetime.time()), axis=1))
    dfr=dfr.drop(['datetime'], axis=1)
    return dfr

#if __name__== "__main__":
    #df = yq.get_quote_data('RELIANCE', '1mo')
    #df = resample_quote_data(df, '2H')