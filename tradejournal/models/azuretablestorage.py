"""
Repository of journalentries that stores data in Azure Table Storage.
"""

from azure.common import AzureMissingResourceHttpError
from azure.storage.table import TableService
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from . import yahooquote
from datetime import datetime
import os, uuid
import arrow
import pytz

from . import Chart, Comment, JournalEntry, JournalEntryNotFound
from . import _load_samples_json

def _partition_and_row_to_key(partition, row):
    """Builds a journalentry/choice key out of azure table partition and row keys."""
    return partition + '_' + row

def _key_to_partition_and_row(key):
    """Parses the azure table partition and row keys from the journalentry/choice
    key."""
    partition, _, row = key.partition('_')
    return partition, row

def _journalentry_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return JournalEntry(_partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def _comment_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Comment(_partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def _chart_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Chart(_partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def strtime_to_timestamp(input):
    if not input:
        return '0'
    else:
        return str(pytz.timezone('Asia/Calcutta').localize(datetime.strptime(input, '%Y-%m-%dT%H:%M')).timestamp())

class Repository(object):
    """Azure Twable Storage repository."""
    def __init__(self, settings):
        """Initializes the repository with the specified settings dict.
        Required settings are:
         - STORAGE_NAME
         - STORAGE_KEY
         - STORAGE_TABLE_POLL
         - STORAGE_TABLE_CHOICE
        """
        self.name = 'Azure Table Storage'
        self.storage_name = settings['STORAGE_NAME']
        self.connection_string = settings['CONNECTION_STRING']
        self.journalentry_table = 'TradeEntryTable'
        self.comments_table = 'CommentsTable'
        self.charts_table = 'ChartsTable'

        self.svc = TableService(self.storage_name, connection_string=self.connection_string)
        self.svc.create_table(self.journalentry_table)
        self.svc.create_table(self.comments_table)
        self.svc.create_table(self.charts_table)

        # Create the BlobServiceClient object which will be used to create a container client
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Create a unique name for the container
        self.container_name = "charts"

        # Create the container
        try:
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        except:
            self.container_client = self.blob_service_client.create_container(self.container_name)

    def get_journalentries(self):
        """Returns all the journalentries from the repository."""
        journalentry_entities = self.svc.query_entities(self.journalentry_table)
        journalentries = [_journalentry_from_entity(entity) for entity in journalentry_entities]
        journalentries.sort(key = lambda x: x.entry_time, reverse=True)
        return journalentries

    def get_journalentry(self, journalentry_key):
        """Returns a journalentry from the repository."""
        try:
            partition, row = _key_to_partition_and_row(journalentry_key)
            journalentry_entity = self.svc.get_entity(self.journalentry_table, partition, row)
            journalentry = _journalentry_from_entity(journalentry_entity)
            return journalentry
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def update_journalentry(self, key, updated_entity):
        """Update the specified journalentry."""
        try:
            partition, row = _key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.journalentry_table, partition, row)
            entity.update(updated_entity)
            key = 'exit_time'
            if key in entity.keys() and entity[key]:
                entity[key] = strtime_to_timestamp(entity[key])
            self.svc.update_entity(self.journalentry_table, entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def add_sample_journalentries(self):
        """Adds a set of journalentries from data stored in a samples.json file."""
        for sample_journalentry in _load_samples_json():
            journalentry_entity = dict(sample_journalentry)
            self.create_journalentries(journalentry_entity)

    def create_journalentries(self, entity):
        """Adds a new journalentry"""
        entry_time = strtime_to_timestamp(entity['entry_time'])
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': entity['symbol'],
            'RowKey': entry_time,
        })
        for key in ['entry_time', 'exit_time']:
            if key in entity.keys():
                entity[key] = strtime_to_timestamp(entity[key])
        self.svc.insert_entity(self.journalentry_table, entity)

    def add_comment(self, key, comment_entity):
        """Add comments"""
        try:
            partition, row = _key_to_partition_and_row(key)
            add_time = str(pytz.UTC.localize(datetime.utcnow()).timestamp())
            comment_entity = dict(comment_entity)
            comment_entity.update(
            {
                'PartitionKey': key,
                'RowKey': add_time,
                'add_time' : add_time
            })
            self.svc.insert_entity(self.comments_table, comment_entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_comments(self, key):
        """Returns all the comments from the repository."""
        partition, row = _key_to_partition_and_row(key)
        comment_entities = self.svc.query_entities(self.comments_table, "PartitionKey eq '%s'"%key)
        comments = [_comment_from_entity(entity) for entity in comment_entities]
        return comments

    def get_all_comments(self):
        """Returns all the comments from the repository."""
        comment_entities = self.svc.query_entities(self.comments_table)
        comments = [_comment_from_entity(entity) for entity in comment_entities]
        comments.sort(key = lambda x: x.add_time, reverse=True)
        return comments

    def add_chart(self, key, entity):
        """Add chart"""
        try:
            partition, row = _key_to_partition_and_row(key)
            add_time = str(datetime.now().timestamp())
            local_file_name = "chart_" + str(uuid.uuid4()) + ".csv"
            entity = dict(entity)
            entity['data'] = local_file_name
            yahooquote.get_yahoo_quote(partition).to_csv(local_file_name, index=False)
            # Create a blob client using the local file name as the name for the blob
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=local_file_name)
            
            # Upload the created file
            with open(local_file_name, "rb") as data:
                blob_client.upload_blob(data)
            
            os.remove(local_file_name)
            entity.update(
            {
                'PartitionKey': key,
                'RowKey': add_time,
                'add_time' : add_time
            })
            self.svc.insert_entity(self.charts_table, entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_charts(self, key):
        """Returns all the charts from the repository."""
        partition, row = _key_to_partition_and_row(key)
        chart_entities = self.svc.query_entities(self.charts_table, "PartitionKey eq '%s'"%key)
        charts = [_chart_from_entity(entity) for entity in chart_entities]
        return charts

    def get_chart_data(self, chartid):
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=chartid)
        data = blob_client.download_blob().readall()
        return data
