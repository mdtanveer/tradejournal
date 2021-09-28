from . import Chart, Comment, JournalEntry, JournalEntryGroup, Trade
import re
import pytz
from datetime import datetime

KEY_ENTRY_TIME = 'entry_time'
KEY_EXIT_TIME = 'exit_time'
KEY_EXIT_PRICE = 'exit_price'
ROLLING_AGE=180
RANGES = {'1h': '6mo', '1d':'2y', '1wk': '5y'}
FWD_BUFFER = {'1h': 2, '2h': 2, '1d':5, '1wk': 15}

def partition_and_row_to_key(partition, row):
    """Builds a journalentry/choice key out of azure table partition and row keys."""
    return partition + '_' + row

def key_to_partition_and_row(key):
    """Parses the azure table partition and row keys from the journalentry/choice
    key."""
    partition, _, row = key.rpartition('_')
    return partition, row

def journalentry_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return JournalEntry(partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def journalentrygroup_from_entity(entity):
    """Creates a journalentrygroup object from the azure table journalentry entity."""
    return JournalEntryGroup(partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def comment_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Comment(partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def chart_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Chart(partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

def trade_from_entity(entity):
    """Creates a journalentry object from the azure table journalentry entity."""
    return Trade(partition_and_row_to_key(entity.PartitionKey, entity.RowKey), entity)

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
