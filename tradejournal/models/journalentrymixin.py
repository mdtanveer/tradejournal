from . import tradejournalutils as tju
import pytz
from datetime import datetime, timedelta
from . import JournalEntry, JournalEntryNotFound, IST_now
from azure.common import AzureMissingResourceHttpError
import calendar

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
        if self.ENTRY_CACHE and not self.has_cache_expired():
            journalentries = list(self.ENTRY_CACHE.values())
            journalentries.sort(key = lambda x: (x.is_open(), x.entry_time), reverse=True)
            return journalentries
        """Returns all the journalentries from the repository."""
        journalentries = self.get_journalentries()
        #comments = self.get_all_comments_for_count()
        #charts = self.get_all_charts_for_count()
        for entry in journalentries:
            entry.comment_count = 0
            entry.chart_count = 0
        self.ENTRY_CACHE = {str(e.key):e for e in journalentries}
        self.last_cache_time = IST_now()
        return journalentries
    
    def get_journalentry_nocache(self, journalentry_key):
        try:
            partition, row = tju.key_to_partition_and_row(journalentry_key)
            journalentry_entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)
            journalentry = tju.journalentry_from_entity(journalentry_entity)
            return journalentry
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()
    
    def get_journalentry(self, journalentry_key, bypass_cache=False):
        """Returns a journalentry from the repository."""
        try:
            if not bypass_cache:
                return self.ENTRY_CACHE[journalentry_key]
            return self.get_journalentry_nocache(journalentry_key)
        except:
            return self.get_journalentry_nocache(journalentry_key)

    def update_journalentry(self, key, input_entity):
        """Update the specified journalentry."""
        try:
            updated_entity = dict(input_entity)
            updated_entity.pop('entry_time')
            updated_entity.pop('symbol')
            partition, row = tju.key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)

            trade_open = (tju.KEY_EXIT_TIME not in entity.keys() 
                              or entity[tju.KEY_EXIT_TIME] == '0'
                              or entity[tju.KEY_EXIT_TIME]  == '')

            trade_closed_in_update = (tju.KEY_EXIT_TIME in updated_entity.keys() 
                                  and updated_entity[tju.KEY_EXIT_TIME] != '0' 
                                  and updated_entity[tju.KEY_EXIT_TIME] != '')

            trade_closure = trade_closed_in_update and trade_open
            
            if trade_closure:
                self.add_chart(key, {'title':'Auto exit chart'}, updated_entity['timeframe'])

            if trade_open and not trade_closed_in_update:
                updated_entity.pop(tju.KEY_EXIT_PRICE)

            entity.update(updated_entity)
            if tju.KEY_EXIT_TIME in entity.keys() and entity[tju.KEY_EXIT_TIME]:
                entity[tju.KEY_EXIT_TIME] = tju.strtime_to_timestamp(entity[tju.KEY_EXIT_TIME])
            self.svc.update_entity(self.TABLES["journalentry"], entity)

            self.ENTRY_CACHE[key] = self.get_journalentry(key, True)

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
            del self.ENTRY_CACHE[key]
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def add_sample_journalentries(self):
        """Adds a set of journalentries from data stored in a samples.json file."""
        for sample_journalentry in tju.load_samples_json():
            journalentry_entity = dict(sample_journalentry)
            self.create_journalentries(journalentry_entity)

    def create_journalentries(self, entity):
        """Adds a new journalentry"""
        entry_time = tju.strtime_to_timestamp(entity[tju.KEY_ENTRY_TIME])
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': entity['symbol'],
            'RowKey': entry_time,
        })
        for key in [tju.KEY_ENTRY_TIME, tju.KEY_EXIT_TIME]:
            if key in entity.keys():
                entity[key] = tju.strtime_to_timestamp(entity[key])
        self.svc.insert_entity(self.TABLES["journalentry"], entity)
        self.add_chart(tju.partition_and_row_to_key(entity['symbol'], entry_time), {'title':'Auto entry chart'}, entity['timeframe'])
        journalentry = tju.journalentry_from_entity(entity)
        self.ENTRY_CACHE[journalentry.key] = journalentry

    def get_journalentry_for_monthly_review(self, year, month, serial):
        lower_timestamp = pytz.UTC.localize(datetime(year, month, 1))
        upper_timestamp = pytz.UTC.localize(datetime(year, month, calendar.monthrange(year, month)[1]))
        query = "RowKey ge '%s' and RowKey le '%s'"%(str(lower_timestamp.timestamp()), str(upper_timestamp.timestamp()))
        journalentries = list(self.svc.query_entities(self.TABLES['journalentry'], query))
        journalentries.sort(key = lambda x: x.entry_time, reverse=True)
        count = len(journalentries)
        if serial >= count or serial < 0:
            serial = 1
        return tju.journalentry_from_entity(journalentries[serial-1])
