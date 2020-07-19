"""
Repository of journalentries that stores data in Azure Table Storage.
"""

from azure.common import AzureMissingResourceHttpError
from azure.cosmosdb.table import TableService
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from . import yahooquote, azurekeyvault
from datetime import datetime, timedelta
import os, uuid
import arrow
import pytz
import requests
import pandas as pd
import re

from . import Chart, Comment, JournalEntry, JournalEntryNotFound, Trade
from . import _load_samples_json, IST_now

KEY_ENTRY_TIME = 'entry_time'
KEY_EXIT_TIME = 'exit_time'

def _partition_and_row_to_key(partition, row):
    """Builds a journalentry/choice key out of azure table partition and row keys."""
    return partition + '_' + row

def _key_to_partition_and_row(key):
    """Parses the azure table partition and row keys from the journalentry/choice
    key."""
    partition, _, row = key.rpartition('_')
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

def _trade_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Trade(_partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def strtime_to_timestamp(input):
    if not input:
        return '0'
    else:
        return str(pytz.timezone('Asia/Calcutta').localize(datetime.strptime(input, '%Y-%m-%dT%H:%M')).timestamp())

def get_symbol(tradingsymbol):
    symbol = re.split(r'\d+', tradingsymbol)[0]
    return symbol

def get_inst_type(tradingsymbol):
    t = re.split(r'\d+', tradingsymbol)[-1]
    if t == 'CE' or t == 'PE':
        return 'option'
    elif t.endswith('FUT'):
        return 'future'
    else:
        return 'default'

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
        self.TABLES = {
            'journalentry' : 'TradeEntryTable',
            'comments' : 'CommentsTable',
            'charts' : 'ChartsTable',
            'trades' : 'TradesTable'
        }
        self.session = None
        self.svc = TableService(self.storage_name, connection_string=self.connection_string)
        for tablename in self.TABLES.values():
            if not self.svc.exists(tablename):
                self.svc.create_table(tablename)

        # Create the BlobServiceClient object which will be used to create a container client
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Create a unique name for the container
        self.container_name = "charts"
        self.kvclient = None

        # Create the container
        try:
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        except:
            self.container_client = self.blob_service_client.create_container(self.container_name)

    def get_journalentries_helper(self, func, age):
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=age)
        query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
        journalentry_entities = self.svc.query_entities(self.TABLES['journalentry'], query)
        journalentries = [func(entity) for entity in journalentry_entities]
        return journalentries

    def get_journalentries(self):
        """Returns all the journalentries from the repository."""
        journalentries = self.get_journalentries_helper(_journalentry_from_entity, 60)
        journalentries.sort(key = lambda x: (x.is_open(), x.entry_time), reverse=True)
        return journalentries

    def get_journalentry(self, journalentry_key):
        """Returns a journalentry from the repository."""
        try:
            partition, row = _key_to_partition_and_row(journalentry_key)
            journalentry_entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)
            journalentry = _journalentry_from_entity(journalentry_entity)
            return journalentry
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def update_journalentry(self, key, input_entity):
        """Update the specified journalentry."""
        try:
            updated_entity = dict(input_entity)
            updated_entity.pop('entry_time')
            updated_entity.pop('symbol')
            partition, row = _key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)

            trade_closure = ((KEY_EXIT_TIME not in entity.keys() 
                              or entity[KEY_EXIT_TIME] == '0'
                              or entity[KEY_EXIT_TIME]  == '') 
                             and (KEY_EXIT_TIME in updated_entity.keys() 
                                  and updated_entity[KEY_EXIT_TIME] != '0' 
                                  and updated_entity[KEY_EXIT_TIME] != ''))
            if trade_closure:
                self.add_chart(key, {'title':'Auto exit chart'}, updated_entity['timeframe'])
            entity.update(updated_entity)
            if KEY_EXIT_TIME in entity.keys() and entity[KEY_EXIT_TIME]:
                entity[KEY_EXIT_TIME] = strtime_to_timestamp(entity[KEY_EXIT_TIME])
            self.svc.update_entity(self.TABLES["journalentry"], entity)

        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def delete_journalentry(self, key):
        """Update the specified journalentry."""
        try:
            #delete comments
            comments = self.get_comments(key)
            for comment in comments:
                partition, row = _key_to_partition_and_row(comment.key)
                self.svc.delete_entity(self.TABLES["comments"], partition, row)

            #delete charts
            charts = self.get_charts(key)
            for chart in charts:
                self.delete_chart(chart.key)

            #delete journal entry
            partition, row = _key_to_partition_and_row(key)
            self.svc.delete_entity(self.TABLES["journalentry"], partition, row)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def add_sample_journalentries(self):
        """Adds a set of journalentries from data stored in a samples.json file."""
        for sample_journalentry in _load_samples_json():
            journalentry_entity = dict(sample_journalentry)
            self.create_journalentries(journalentry_entity)

    def create_journalentries(self, entity):
        """Adds a new journalentry"""
        entry_time = strtime_to_timestamp(entity[KEY_ENTRY_TIME])
        entity = dict(entity)
        entity.update(
        {
            'PartitionKey': entity['symbol'],
            'RowKey': entry_time,
        })
        for key in [KEY_ENTRY_TIME, KEY_EXIT_TIME]:
            if key in entity.keys():
                entity[key] = strtime_to_timestamp(entity[key])
        self.svc.insert_entity(self.TABLES["journalentry"], entity)
        self.add_chart(_partition_and_row_to_key(entity['symbol'], entry_time), {'title':'Auto entry chart'}, entity['timeframe'])

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
            self.svc.insert_entity(self.TABLES["comments"], comment_entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_comments(self, key):
        """Returns all the comments from the repository."""
        partition, row = _key_to_partition_and_row(key)
        comment_entities = self.svc.query_entities(self.TABLES["comments"], "PartitionKey eq '%s'"%key)
        comments = [_comment_from_entity(entity) for entity in comment_entities]
        return comments

    def get_all_comments(self):
        """Returns all the comments from the repository."""
        comment_entities = self.svc.query_entities(self.TABLES["comments"])
        comments = [_comment_from_entity(entity) for entity in comment_entities]
        comments.sort(key = lambda x: x.add_time, reverse=True)
        return comments

    def add_chart(self, key, entity, timeframe):
        """Add chart"""
        if not timeframe or timeframe == '2h':
            timeframe = '1h'
        RANGES = {'1h': '60d', '1d':'250d', '1wk': '900d'}
        try:
            partition, row = _key_to_partition_and_row(key)
            add_time = str(datetime.now().timestamp())
            local_file_name = "chart_" + str(uuid.uuid4()) + ".csv"
            entity = dict(entity)
            entity['data'] = local_file_name
            yahooquote.get_yahoo_quote(partition, RANGES[timeframe], timeframe).to_csv(local_file_name, index=False)
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
            self.svc.insert_entity(self.TABLES["charts"], entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def delete_chart(self, key):
        try:
            partition, row = _key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES["charts"], partition, row)
            file_name = entity['data']
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_name)
            blob_client.delete_blob()
            self.svc.delete_entity(self.TABLES["charts"], partition, row)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_charts(self, key):
        """Returns all the charts from the repository."""
        partition, row = _key_to_partition_and_row(key)
        chart_entities = self.svc.query_entities(self.TABLES["charts"], "PartitionKey eq '%s'"%key)
        charts = [_chart_from_entity(entity) for entity in chart_entities]
        return charts

    def get_chart_data(self, chartid):
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=chartid)
        data = blob_client.download_blob().readall()
        return data

    def get_trades(self, journalentry_key):
        partition, row = _key_to_partition_and_row(journalentry_key)
        journalentry = self.get_journalentry(journalentry_key)
        trade_entities = []
        if journalentry.has_valid_entry_time():
            lower_timestamp = journalentry.entry_time - timedelta(minutes=15)
            query = "PartitionKey eq '%s' and RowKey ge '%s'"%(partition, str(lower_timestamp.timestamp()))
            if journalentry.has_valid_exit_time():
                upper_timestamp = journalentry.exit_time + timedelta(minutes=15)
                query += " and RowKey le '%s'"%(str(upper_timestamp.timestamp()))
            trade_entities = self.svc.query_entities(self.TABLES["trades"], query)
        trades = [_trade_from_entity(entity) for entity in trade_entities]
        return trades

    def get_all_trades(self):
        """Returns all the trades from the repository."""
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=30)
        query = "RowKey ge '%s'"%str(lower_timestamp.timestamp())
        trade_entities = self.svc.query_entities(self.TABLES["trades"], query)
        trades = [_trade_from_entity(entity) for entity in trade_entities]
        trades.sort(key = lambda x: x.date, reverse=True)
        return trades

    def get_position_data(self):
        if not self.kvclient:
            self.kvclient = azurekeyvault.AzureKeyVaultClient()
            self.kvclient.fetch_secrets()

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
        df['symbol'] = df['tradingsymbol'].apply(get_symbol)
        df['itype'] = df['tradingsymbol'].apply(get_inst_type)

        trades = self.get_journalentries_helper(lambda x:x, 60)
        tdf = pd.DataFrame(trades)
        tdf = tdf.query('(exit_time =="0" | exit_time == "") & is_idea !="Y"')
        tdf = tdf[['symbol','strategy', 'timeframe']]

        out = df.merge(tdf, left_on='symbol', right_on='symbol', how='left')
        grp = out.groupby('itype')

        position_data = []
        for groupname in grp.groups.keys():
            cols = list(COLUMNS)
            cols.extend(['strategy', 'timeframe'])
            df = grp.get_group(groupname)[cols]
            position_data.append((groupname, df.to_html(index=False, classes='table table-hover')))

        return position_data


