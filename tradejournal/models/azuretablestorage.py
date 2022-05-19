"""
Repository of journalentries that stores data in Azure Table Storage.
"""

from azure.cosmosdb.table import TableService
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

from .chartmixin import ChartMixin
from .journalentrymixin import JournalEntryMixin
from .journalentrygroupmixin import JournalEntryGroupMixin
from .commentmixin import CommentMixin
from .trademixin import TradeMixin
from .positionmixin import PositionMixin
from .tradesignalsmixin import TradeSignalsMixin
from . import IST_now 

class Repository(JournalEntryMixin, ChartMixin,
        CommentMixin, TradeMixin, PositionMixin, TradeSignalsMixin, JournalEntryGroupMixin):
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
            'trades' : 'TradesTable',
            'summarypnl': 'SummaryPnLTable',
            'tradesignals': 'TradeSignalsTable',
            'journalentrygroup': 'TradeEntryGroupTable'
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
        self.GROUP_CACHE = {}
        self.ENTRY_CACHE = {}
        self.last_cache_time = None

    def has_cache_expired(self):
        return self.last_cache_time.day != IST_now().day
