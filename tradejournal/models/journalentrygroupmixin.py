from . import tradejournalutils as tju
import pytz
from datetime import datetime, timedelta
from . import JournalEntryGroup, JournalEntryNotFound
from azure.common import AzureMissingResourceHttpError
import calendar
import uuid

class JournalEntryGroupMixin:
    def get_journalentrygroups_helper(self, func, age):
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=age)
        query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
        journalentrygroup_entities = self.svc.query_entities(self.TABLES['journalentrygroup'], query)
        journalentrygroups = [func(entity) for entity in journalentrygroup_entities]
        return journalentrygroups

    def get_journalentrygroups(self):
        """Returns all the journalentrygroups from the repository."""
        journalentrygroups = self.get_journalentrygroups_helper(tju.journalentrygroup_from_entity, tju.ROLLING_AGE)
        journalentrygroups.sort(key = lambda x: (x.is_open(), x.entry_time), reverse=True)
        return journalentrygroups

    def get_journalentrygroups_forview(self, alljournalentries):
        """Returns all the journalentrygroups from the repository."""
        journalentrygroups = self.get_journalentrygroups()
        self.GROUP_CACHE = {str(e.key):e for e in journalentrygroups}
        #comments = self.get_all_comments_for_count()
        indict = dict(self.ENTRY_CACHE)
        indict.update(self.GROUP_CACHE)
        
        for entry in journalentrygroups:
            entry.comment_count = 0
            entry.populate_children(indict, alljournalentries)
            self.GROUP_CACHE[entry.key] = entry
        return journalentrygroups
 
    def invalidate_journalentrygroupcache(self, journalentrygroup_key):
        try:
            del self.GROUP_CACHE[journalentrygroup_key]
        except:
            pass

    def get_journalentrygroup(self, journalentrygroup_key):
        """Returns a journalentrygroup from the repository."""
        try:
            return self.GROUP_CACHE[journalentrygroup_key]
        except:
            try:
                partition, row = tju.key_to_partition_and_row(journalentrygroup_key)
                journalentrygroup_entity = self.svc.get_entity(self.TABLES['journalentrygroup'], partition, row)
                journalentrygroup = tju.journalentrygroup_from_entity(journalentrygroup_entity)
                indict = dict(self.ENTRY_CACHE)
                indict.update(self.GROUP_CACHE)
                journalentrygroup.populate_children(indict, [])
                return journalentrygroup
            except AzureMissingResourceHttpError:
                raise JournalEntrygroupNotFound()

    def update_journalentrygroup(self, key, input_entity):
        """Update the specified journalentrygroup."""
        try:
            updated_entity = dict(input_entity)
            updated_entity.pop('entry_time')
            partition, row = tju.key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES['journalentrygroup'], partition, row)
            entity.update(updated_entity)
            if tju.KEY_EXIT_TIME in entity.keys() and entity[tju.KEY_EXIT_TIME]:
                entity[tju.KEY_EXIT_TIME] = tju.strtime_to_timestamp(entity[tju.KEY_EXIT_TIME])
            self.svc.update_entity(self.TABLES["journalentrygroup"], entity)
            self.invalidate_journalentrygroupcache(key)

        except AzureMissingResourceHttpError:
            raise JournalEntrygroupNotFound()

    def delete_journalentrygroup(self, key):
        """Update the specified journalentrygroup."""
        try:
            #delete comments
            comments = self.get_comments(key)
            for comment in comments:
                partition, row = tju.key_to_partition_and_row(comment.key)
                self.svc.delete_entity(self.TABLES["comments"], partition, row)

            #delete journal entry
            partition, row = tju.key_to_partition_and_row(key)
            self.svc.delete_entity(self.TABLES["journalentrygroup"], partition, row)
            self.invalidate_journalentrygroupcache(key)
        except AzureMissingResourceHttpError:
            raise JournalEntrygroupNotFound()

    def create_journalentrygroup(self, entity):
        """Adds a new journalentrygroup"""
        entry_time = tju.strtime_to_timestamp(entity[tju.KEY_ENTRY_TIME])
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': str(uuid.uuid4()),
            'RowKey': entry_time,
        })
        for key in [tju.KEY_ENTRY_TIME, tju.KEY_EXIT_TIME]:
            if key in entity.keys():
                entity[key] = tju.strtime_to_timestamp(entity[key])
        self.svc.insert_entity(self.TABLES["journalentrygroup"], entity)
        journalentrygroup = tju.journalentrygroup_from_entity(entity)
        self.GROUP_CACHE[journalentrygroup.key] = journalentrygroup

    def get_journalentrygroup_for_monthly_review(self, year, month, serial):
        lower_timestamp = pytz.UTC.localize(datetime(year, month, 1))
        upper_timestamp = pytz.UTC.localize(datetime(year, month, calendar.monthrange(year, month)[1]))
        query = "RowKey ge '%s' and RowKey le '%s'"%(str(lower_timestamp.timestamp()), str(upper_timestamp.timestamp()))
        journalentrygroups = list(self.svc.query_entities(self.TABLES['journalentrygroup'], query))
        journalentrygroups.sort(key = lambda x: x.entry_time, reverse=True)
        count = len(journalentrygroups)
        if serial >= count or serial < 0:
            serial = 1
        return tju.journalentrygroup_from_entity(journalentrygroups[serial-1])

    def copyattributestochildren(self, parententity):
        for je in parententity.deserialized_items:
            if not je.is_group():
                update = {
                        'strategy' : parententity.strategy
                }
                print(update)
                self.update_journalentry(je.key, update)
            else:
                self.copyattributestochildren(je)


