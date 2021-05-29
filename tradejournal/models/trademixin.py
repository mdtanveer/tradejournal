from . import tradejournalutils as tju
from datetime import datetime, timedelta
import pytz

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

