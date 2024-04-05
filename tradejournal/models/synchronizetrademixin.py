from . import tradejournalutils as tju
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np

def toIST_fromtimestamp(ts):
    return pytz.UTC.localize(datetime.utcfromtimestamp(ts)).astimezone(pytz.timezone('Asia/Calcutta'))

def todate(ts):
    d = toIST_fromtimestamp(float(ts))
    return d.date()

class SynchronizeTradeMixin:
    class AtsClient:
        def __init__(self, tablesvc):
            self.svc = tablesvc

        def insert_to_ats(self, df, tablename):
            json_rows = df.apply(lambda x: x.to_dict(), axis=1)
            for i in range(0, json_rows.size):
                row = json_rows.iloc[i]
                try:
                    self.svc.insert_entity(tablename,row)
                except:
                    print(tablename, row)
                    raise

        def update_to_ats(self, df, tablename):
            json_rows = df.apply(lambda x: x.to_dict(), axis=1)
            for i in range(0, json_rows.size):
                row = json_rows.iloc[i]
                self.svc.merge_entity(tablename,row)

        def upsert_to_ats(self, df, tablename):
            json_rows = df.apply(lambda x: x.to_dict(), axis=1)
            for i in range(0, json_rows.size):
                row = json_rows.iloc[i]
                self.svc.insert_or_replace_entity(tablename,row)

        def fetch_data_from_ats(self, tablename, age):
            lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=age)
            query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
            entities = self.svc.query_entities(tablename, query)
            df = pd.DataFrame(entities)
            return df

    @staticmethod
    def split_trades(df):
        cumsum = 0
        group = 0
        ndf_lst = []
        result = []
        for i in range(0, df.shape[0]):
            prev = cumsum
            cumsum += df.iloc[i]['quantity1']
            ndf_lst.append(df.iloc[i])
            if cumsum == 0:
                result.append(pd.concat(ndf_lst, axis=1).transpose())
                ndf_lst=[]
            elif np.sign(prev)*np.sign(cumsum) < 0:
                ndf_lst[-1].loc['quantity1'] = -prev
                result.append(pd.concat(ndf_lst, axis=1).transpose())
                
                ndf_lst = [df.iloc[i]]
                ndf_lst[-1].loc['quantity1'] = df.iloc[i]['quantity1']+prev
        if len(ndf_lst) > 0:
            result.append(pd.concat(ndf_lst, axis=1).transpose())

        return result

    @staticmethod
    def distill_dataframe_into_trade(df, closed=True):
        #expecting a series of trades with first row as initiating trade and last row as closing trade
        prices = df.groupby("trade_type").apply(lambda x: np.average(x.price, weights=x.quantity))
        entry_price = prices[df['trade_type'].iloc[0]]
        tradingsymbol = df['tradingsymbol'].iloc[0]
        timeframe = '2h' if tradingsymbol.endswith('FUT') else '1d'
        row = {
            'PartitionKey' : df['PartitionKey'].iloc[0],
             'direction' : 'LONG' if df['trade_type'].iloc[0] == 'buy' else 'SHORT',
             'entry_price' : entry_price,
             'entry_sl' : '',
             'entry_target' : '',
             'entry_time' : df['RowKey'].iloc[0],
             'exit_price' : '',
             'exit_time' : '',
             'is_idea' : '',
             'quantity' : df['quantity'].iloc[0],
             'rating' : '',
             'strategy' : 'default',
             'symbol' : df['PartitionKey'].iloc[0],
             'timeframe': timeframe,
             'tradingsymbol': tradingsymbol,
             'exchange': df['exchange'].iloc[0]
        }
        if closed:
            closure_type = 'sell' if df['trade_type'].iloc[0] == 'buy' else 'buy'
            exit_price = prices[closure_type]
            row['exit_price'] = exit_price
            row['exit_time'] = df['RowKey'].iloc[-1]
        row['closed'] = closed
        return row

    class ZerodhaClient():
        def __init__(self):
            self.kvclient = None
            self.session = None

        def get_position_data(self):
            try:
                if not self.kvclient:
                    self.kvclient = AzureKeyVaultClient()
                    self.kvclient.get_azure_keyvault_secrets()

                data_found = False
                if self.session:
                    z = self.session.get("https://kite.zerodha.com/oms/portfolio/positions")
                    data_found = (z.status_code == 200)
                if not data_found:
                    self.session = requests.Session()
                    x = self.session.post("https://kite.zerodha.com/api/login", 
                                          data = {'user_id': self.kvclient.get_secret('zerodha-login'), 
                                                  'password': self.kvclient.get_secret('zerodha-password')})
                    res = x.json()
                    tfd = res['data']
                    del(tfd['twofa_type'])
                    del(tfd['twofa_status'])
                    tfd['twofa_value'] = self.kvclient.get_secret('zerodha-pin')
                    y = self.session.post("https://kite.zerodha.com/api/twofa", data = tfd)
                    self.session.headers.update({'Authorization': 'enctoken '+y.cookies['enctoken']})
                    z = self.session.get("https://kite.zerodha.com/oms/portfolio/positions")
                data = z.json()['data']['net']
                df = pd.DataFrame(data)
                COLUMNS = ['tradingsymbol', 'quantity', 'average_price', 'last_price', 'unrealised']
                df = df[COLUMNS]
                df['symbol'] = df['tradingsymbol'].apply(tju.get_symbol)
                return df
            except:
                return pd.DataFrame()

    @staticmethod
    def get_trades_and_journalentries(atsClient, age):
        tdf = atsClient.fetch_data_from_ats('TradesTable', age)
        if not tdf.empty:
            grps = tdf.sort_values(by='RowKey').groupby(['PartitionKey', 'tradingsymbol'])
            trades = []
            for groupidx in grps.groups:
                df = grps.get_group(groupidx)
                df['quantity1'] = df.apply(lambda r: r['quantity'] if r['trade_type'] == 'buy' else -r['quantity'], axis=1)
                #df['sum'] = df['quantity1'].cumsum()
                #cdfs = np.split(df, np.where(df['sum'] == 0)[0]+1)  
                splits = SynchronizeTradeMixin.split_trades(df)
                for d in splits:
                    closed = d['quantity1'].sum() == 0
                    trades.append(SynchronizeTradeMixin.distill_dataframe_into_trade(d, closed))
            trades = pd.DataFrame(trades)
            trades['entry_date'] = trades['entry_time'].apply(todate)
        else:
            trades = pd.DataFrame()
        jdf = atsClient.fetch_data_from_ats('TradeEntryTable', age)
        if not jdf.empty and not trades.empty:
            jdf['entry_date'] = jdf['entry_time'].apply(todate)
            df = pd.merge(trades, jdf[['PartitionKey', 'RowKey', 'entry_date', 'tradingsymbol']], left_on=['PartitionKey','entry_date','tradingsymbol'],
                    right_on=['PartitionKey','entry_date','tradingsymbol'], how="left", indicator=True)
        elif jdf.empty:
            df = trades
            df["_merge"] = "left_only"
        elif trades.empty:
            jdf['entry_date'] = jdf['entry_time'].apply(todate)
            df = jdf
            df["_merge"] = "left_only"

        return df, jdf, tdf

    @staticmethod
    def get_sync_delta(df):
        open_positions = pd.DataFrame()
        DROP_COLS=['closed', 'entry_date', '_merge']

        open_insert = pd.DataFrame()
        open_update = pd.DataFrame()
        closed_insert = pd.DataFrame()
        closed_update = pd.DataFrame()
        if not df.empty:
            open_insert = df.query('_merge=="left_only" & closed ==False').drop(DROP_COLS, axis=1)
            open_update = df.query('_merge=="both" & closed == False').drop(DROP_COLS, axis=1)

            if not open_positions.empty:
                open_insert = pd.merge(open_insert, open_positions['tradingsymbol'],
                        on=['tradingsymbol', 'tradingsymbol']) .drop(DROP_COLS, axis=1)
                open_update = pd.merge(open_update, open_positions['tradingsymbol'],
                        on=['tradingsymbol', 'tradingsymbol']) .drop(DROP_COLS, axis=1)

            closed_insert = df.query('_merge=="left_only" & closed ==True').drop(DROP_COLS, axis=1)
            closed_update = df.query('_merge=="both" & closed == True').drop(DROP_COLS, axis=1)

        update_df = pd.concat([open_update, closed_update], axis=0)
        insert_df = pd.concat([open_insert, closed_insert], axis=0)

        return update_df, insert_df
        
    def sync_journal_with_trades(self, age=60):
        self.atsClient = self.AtsClient(self.svc)
        df, _, _ = SynchronizeTradeMixin.get_trades_and_journalentries(self.atsClient, age)
        update_df, insert_df = SynchronizeTradeMixin.get_sync_delta(df)

        if not insert_df.empty:
            insert_df['RowKey'] = insert_df['entry_time']
            insert_df = insert_df.astype(str)
            self.atsClient.insert_to_ats(insert_df, 'TradeEntryTable')

        if not update_df.empty:
            update_df = update_df[['PartitionKey', 'entry_price', 'exit_price', 'exit_time', 'quantity', 'RowKey', 'tradingsymbol']]
            update_df = update_df.astype(str)

            self.atsClient.update_to_ats(update_df, 'TradeEntryTable')

