from . import tradejournalutils as tju
import pytz
from datetime import datetime, timedelta
from . import JournalEntry, JournalEntryNotFound
from azure.common import AzureMissingResourceHttpError

class JournalEntryMixin:
    def get_journalentries_helper(self, func, age):
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=age)
        query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
        journalentry_entities = self.svc.query_entities(self.TABLES['journalentry'], query)
        journalentries = [func(entity) for entity in journalentry_entities]
        return journalentries

    def get_journalentries(self):
        """Returns all the journalentries from the repository."""
        journalentries = self.get_journalentries_helper(tju.journalentry_from_entity, tju.ROLLING_AGE)
        journalentries.sort(key = lambda x: (x.is_open(), x.entry_time), reverse=True)
        return journalentries

    def get_journalentries_forview(self):
        """Returns all the journalentries from the repository."""
        journalentries = self.get_journalentries()
        comments = self.get_all_comments_for_count()
        charts = self.get_all_charts_for_count()
        for entry in journalentries:
            entry.comment_count = len(list(filter(lambda x: x['PartitionKey']==entry.key, comments)))
            entry.chart_count = len(list(filter(lambda x: x['PartitionKey']==entry.key, charts)))
        return journalentries
    
    def get_journalentry(self, journalentry_key):
        """Returns a journalentry from the repository."""
        try:
            partition, row = tju.key_to_partition_and_row(journalentry_key)
            journalentry_entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)
            journalentry = tju.journalentry_from_entity(journalentry_entity)
            return journalentry
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def update_journalentry(self, key, input_entity):
        """Update the specified journalentry."""
        try:
            updated_entity = dict(input_entity)
            updated_entity.pop('entry_time')
            updated_entity.pop('symbol')
            partition, row = tju.key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)

            trade_closure = ((tju.KEY_EXIT_TIME not in entity.keys() 
                              or entity[tju.KEY_EXIT_TIME] == '0'
                              or entity[tju.KEY_EXIT_TIME]  == '') 
                             and (tju.KEY_EXIT_TIME in updated_entity.keys() 
                                  and updated_entity[tju.KEY_EXIT_TIME] != '0' 
                                  and updated_entity[tju.KEY_EXIT_TIME] != ''))
            if trade_closure:
                self.add_chart(key, {'title':'Auto exit chart'}, updated_entity['timeframe'])
            entity.update(updated_entity)
            if tju.KEY_EXIT_TIME in entity.keys() and entity[KEY_EXIT_TIME]:
                entity[tju.KEY_EXIT_TIME] = strtime_to_timestamp(entity[KEY_EXIT_TIME])
            self.svc.update_entity(self.TABLES["journalentry"], entity)

        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def delete_journalentry(self, key):
        """Update the specified journalentry."""
        try:
            #delete comments
            comments = self.get_comments(key)
            for comment in comments:
                partition, row = tju.key_to_partition_and_row(comment.key)
                self.svc.delete_entity(self.TABLES["comments"], partition, row)

            #delete charts
            charts = self.get_charts(key)
            for chart in charts:
                self.delete_chart(chart.key)

            #delete journal entry
            partition, row = tju.key_to_partition_and_row(key)
            self.svc.delete_entity(self.TABLES["journalentry"], partition, row)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def add_sample_journalentries(self):
        """Adds a set of journalentries from data stored in a samples.json file."""
        for sample_journalentry in tju.load_samples_json():
            journalentry_entity = dict(sample_journalentry)
            self.create_journalentries(journalentry_entity)

    def create_journalentries(self, entity):
        """Adds a new journalentry"""
        entry_time = strtime_to_timestamp(entity[tju.KEY_ENTRY_TIME])
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': entity['symbol'],
            'RowKey': entry_time,
        })
        for key in [tju.KEY_ENTRY_TIME, tju.KEY_EXIT_TIME]:
            if key in entity.keys():
                entity[key] = strtime_to_timestamp(entity[key])
        self.svc.insert_entity(self.TABLES["journalentry"], entity)
        self.add_chart(tju.partition_and_row_to_key(entity['symbol'], entry_time), {'title':'Auto entry chart'}, entity['timeframe'])