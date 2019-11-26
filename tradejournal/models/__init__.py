"""
Package for the models.
"""

from os import path
import json
from datetime import datetime

class JournalEntry(object):
    """Corresponds to one entry in trade journal"""
    def __init__(self):
        self.key = ""
        self.symbol = ""
        self.entry_time = None
        self.exit_time = None
        self.entry_price = 0
        self.exit_price = 0
        self.quantity = 0
        self.entry_sl = 0
        self.entry_target = 0
        self.direction = "LONG"

    def __init__(self, key, entity): 
        self.key = key
        self.symbol = entity.symbol
        self.entry_time = datetime.fromtimestamp(float(entity.entry_time))
        self.exit_time = datetime.fromtimestamp(float(entity.exit_time))
        self.entry_price = entity.entry_price
        self.exit_price = entity.exit_price
        self.quantity = entity.quantity
        self.entry_sl = entity.entry_sl
        self.entry_target = entity.entry_target
        self.direction = entity.direction

class JournalEntryNotFound(Exception):
    """Exception raised when a trade entry object couldn't be retrieved from
    the repository."""
    pass

def _load_samples_json():
    """Loads polls from samples.json file."""
    samples_path = path.join(path.dirname(__file__), 'samples.json')
    with open(samples_path, 'r') as samples_file:
        return json.load(samples_file)
