from . import tradejournalutils as tju
from datetime import datetime, timedelta
from . import yahooquotes, resample
import pytz
from azure.common import AzureMissingResourceHttpError
import os, uuid
from io import StringIO
import pandas as pd

pd.set_option("display.precision", 2)

class ChartMixin:
    def get_chart_data_from_yahoo(self, symbol, timeframe, context_date=None):
        #For intraday data is always returned in 1h timeframe
        if not timeframe or timeframe == '2h':
            timeframe = '1h'
        preferred_exc = '.BO' if timeframe == '1h' else '.NS'
        df = yahooquotes.get_quote_data(symbol, tju.RANGES[timeframe], timeframe,
                preferred_exc, context_date)
        return df

    def add_chart(self, key, entity, timeframe):
        """Add chart"""
        try:
            partition, row = tju.key_to_partition_and_row(key)

            journalentry_entity = self.svc.get_entity(self.TABLES['journalentry'], partition, row)
            journalentry = tju.journalentry_from_entity(journalentry_entity)
            context_date = None
            if journalentry.has_valid_exit_time():
                context_date = journalentry.exit_time + timedelta(days=tju.FWD_BUFFER[timeframe])
            elif journalentry.has_valid_entry_time():
                context_date = journalentry.exit_time + timedelta(days=tju.FWD_BUFFER[timeframe])

            add_time = str(datetime.now().timestamp())
            local_file_name = "chart_" + str(uuid.uuid4()) + ".csv"
            entity = dict(entity)
            entity['data'] = local_file_name
            yd = self.get_chart_data_from_yahoo(partition, timeframe, context_date)
            yd.to_csv(local_file_name, index=False)
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
            partition, row = tju.key_to_partition_and_row(key)
            entity = self.svc.get_entity(self.TABLES["charts"], partition, row)
            file_name = entity['data']
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_name)
            blob_client.delete_blob()
            self.svc.delete_entity(self.TABLES["charts"], partition, row)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_charts(self, key):
        """Returns all the charts from the repository."""
        partition, row = tju.key_to_partition_and_row(key)
        chart_entities = self.svc.query_entities(self.TABLES["charts"], "PartitionKey eq '%s'"%key)
        charts = [tju.chart_from_entity(entity) for entity in chart_entities]
        return charts

    def get_all_charts(self):
        """Returns all the comments from the repository."""
        chart_entities = self.svc.query_entities(self.TABLES["charts"])
        charts = [tju.chart_from_entity(entity) for entity in chart_entities]
        return charts

    def get_all_charts_for_count(self):
        """Returns all the comments from the repository for counting"""
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=tju.ROLLING_AGE)
        query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
        chart_entities = self.svc.query_entities(self.TABLES["charts"], query, select="PartitionKey")
        return chart_entities

    def resample_data(self, data, target_tf):
        df = pd.read_csv(StringIO(data.decode('ascii')))
        data = resample.resample_quote_data(df, target_tf).to_csv(index=False)
        return data

    def get_chart_data(self, chartid, tf, typ):
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=chartid)
        data = blob_client.download_blob().readall()
        if typ == 'original':
            if tf == '2h':
                data = self.resample_data(data, '2H')
        elif typ == 'mother':
            MOTHER_CHART_TF={'2h': '1D', '1d': '1W', '1W': '1M'}
            data = self.resample_data(data, MOTHER_CHART_TF[tf])
        elif typ.startswith('latest'):
            symbol = typ.split('_')[1]
            df = self.get_chart_data_from_yahoo(symbol, tf)
            if tf == '2h':
                data = resample.resample_quote_data(df, '2H').to_csv(index=False)
            else:
                data = df.to_csv(index=False)
        return data
