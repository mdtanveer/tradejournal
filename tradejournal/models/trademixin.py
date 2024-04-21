from . import tradejournalutils as tju
from datetime import datetime, timedelta
import pytz
import pandas as pd

class TradeMixin:
    def get_trades(self, journalentry_key):
        partition, row = tju.key_to_partition_and_row(journalentry_key)
        journalentry = self.get_journalentry(journalentry_key)
        trade_entities = []
        if journalentry.has_valid_entry_time():
            lower_timestamp = journalentry.entry_time - timedelta(minutes=15)
            query = "PartitionKey eq '%s' and RowKey ge '%s'"%(partition, str(lower_timestamp.timestamp()))
            if journalentry.has_valid_exit_time():
                upper_timestamp = journalentry.exit_time + timedelta(minutes=15)
                query += " and RowKey le '%s'"%(str(upper_timestamp.timestamp()))
            trade_entities = self.svc.query_entities(self.TABLES["trades"], query)
        trades = [tju.trade_from_entity(entity) for entity in trade_entities]
        return trades

    def get_all_trades(self):
        """Returns all the trades from the repository."""
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=30)
        query = "RowKey ge '%s'"%str(lower_timestamp.timestamp())
        trade_entities = self.svc.query_entities(self.TABLES["trades"], query)
        trades = [tju.trade_from_entity(entity) for entity in trade_entities]
        trades.sort(key = lambda x: x.date, reverse=True)
        return trades


    def get_summary_pnl(self):
        """Returns all the summary pnl from the repository."""
        summaries = self.svc.query_entities(self.TABLES["summarypnl"])
        return summaries

    def process_tradesync(self, fin):
        self.upload_from_csv_to_ats(fin)

    def upload_to_ats(self, df):
        tablename = 'TradesTable'
        json_rows = df.apply(lambda x: x.to_dict(), axis=1)
        for i in range(0, json_rows.size):
            row = json_rows.iloc[i]
            # azurite bug workaround for roundtriping whole number as Int32
            row["price@odata.type"] = "Edm.Double"
            self.svc.insert_or_replace_entity(tablename,row)
   
    def strtime_to_timestamp(self, input):
        if not input:
            return '0'
        else:
            return str(pytz.timezone('Asia/Calcutta').localize(datetime.strptime(input, '%Y-%m-%dT%H:%M:%S')).timestamp())

    def upload_from_csv_to_ats(self, csvfile, exchange="NFO"):
        df = pd.read_csv(csvfile, dtype={'quantity':'int64', 'price':'float64'})
        df.rename(columns={'symbol':'tradingsymbol'}, inplace=True)

        dfg = df.groupby('order_id').agg({'tradingsymbol':'first','price':'mean', 'order_execution_time':'last', 'quantity':'sum', 'trade_type':'first'})
        dfg2=dfg.sort_values(['tradingsymbol', 'order_execution_time'])
        dfg2['PartitionKey'] = dfg2['tradingsymbol'].apply(tju.get_symbol)
        dfg2['RowKey'] = dfg2['order_execution_time'].apply(self.strtime_to_timestamp)
        dfg2['exchange'] = exchange
        dfg2 = dfg2.drop(columns=['order_execution_time']).round(2)

        self.upload_to_ats(dfg2)


