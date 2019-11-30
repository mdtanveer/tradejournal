"""
Package for the models.
"""

from os import path
import json
from datetime import datetime

class JournalEntry(object):
    """Corresponds to one entry in trade journal"""
    def __init__(self, key, entity): 
        self.key = key
        self.symbol = entity.symbol
        self.entry_time = datetime.fromtimestamp(float(entity.entry_time))
        self.exit_time = datetime.fromtimestamp(float(entity.exit_time if 'exit_time' in entity.keys() else '0'))
        self.entry_price = entity.entry_price if 'entry_price' in entity.keys() else ''
        self.exit_price = entity.exit_price if 'exit_price' in entity.keys() else '' 
        self.quantity = entity.quantity if 'quantity' in entity.keys() else ''
        self.entry_sl = entity.entry_sl if 'entry_sl' in entity.keys() else ''
        self.entry_target = entity.entry_target if 'entry_target' in entity.keys() else ''
        self.direction = entity.direction if 'direction' in entity.keys() else ''

class JournalEntryNotFound(Exception):
    """Exception raised when a trade entry object couldn't be retrieved from
    the repository."""
    pass

class Comment(object):
    def __init__(self, key, entity): 
        self.key = key
        self.add_time = datetime.fromtimestamp(float(entity.add_time))                                               
        self.title = entity.title if 'title' in entity.keys() else ''
        self.text = entity.text if 'text' in entity.keys() else ''

class Chart(object):
    def __init__(self, key, entity): 
        self.key = key
        #self.add_time = datetime.fromtimestamp(float(entity.add_time))                                               
        self.title = entity.title if 'title' in entity.keys() else ''
        self.data = entity.data

def _load_samples_json():
    """Loads polls from samples.json file."""
    samples_path = path.join(path.dirname(__file__), 'samples.json')
    with open(samples_path, 'r') as samples_file:
        return json.load(samples_file)
