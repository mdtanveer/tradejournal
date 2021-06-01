from . import tradejournalutils as tju
from datetime import datetime, timedelta
from . import TradeSignal

class TradeSignalsMixin:
    def get_tradesignals(self, date, timeframe, strategy):
        query = f"PartitionKey eq '{date}_{timeframe}_{strategy}'"
        tradesignal_entity = self.svc.query_entities(self.TABLES['tradesignals'], query)
        tradesignals = [TradeSignal(t) for t in tradesignal_entity]
        return tradesignals

    def create_tradesignal(self, date, timeframe, strategy, entity):
        """Adds a new tradesignal"""
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': '_'.join([date, timeframe, strategy]),
            'RowKey': '_'.join([entity['symbol']]),
        })
        self.svc.insert_or_replace_entity(self.TABLES["tradesignals"], entity)

    def create_tradesignals(self, date, timeframe, entities):
        for strategy_dict in entities:
            for strategy, tradesignals in strategy_dict.items():
                for entity in tradesignals:
                    self.create_tradesignal(date, timeframe, strategy, entity)
