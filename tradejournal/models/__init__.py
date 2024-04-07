"""
Package for the models.
"""

from os import path
import json
from datetime import datetime, timedelta
import arrow
import pytz
from . import stockutils
import itertools, functools
import re

def IST_now():
    return pytz.UTC.localize(datetime.utcnow()).astimezone(pytz.timezone('Asia/Calcutta'))

def toIST_fromtimestamp(ts):
    return pytz.UTC.localize(datetime.utcfromtimestamp(ts)).astimezone(pytz.timezone('Asia/Calcutta'))

class JournalEntryGroup(object):
    """Corresponds to one entry in trade journal"""
    def __init__(self, key, entity): 
        self.key = key
        try:
            self.entry_time = toIST_fromtimestamp(float(entity['entry_time']))
        except:
            self.entry_time = toIST_fromtimestamp(0)
        try:
            self.exit_time = toIST_fromtimestamp(float(entity['exit_time']))
        except:
            self.exit_time = toIST_fromtimestamp(0)
        self.rating = entity['rating'] if 'rating' in entity.keys() else ''
        self.strategy = entity['strategy'] if 'strategy' in entity.keys() and not not entity['strategy'] else 'default'
        self.comment_count = 0
        self.name = entity['name'] if 'name' in entity.keys() else ''
        self.items = entity["items"] if 'items' in entity.keys() else ''
        self.deserialized_items = []

    def populate_children(self, indict, alljournalentries):
        if not self.items:
            return
        keys = self.items.split(',')
        for key in keys:
            try:
                key = key.strip()
                self.deserialized_items.append(indict[key])
                if indict[key] in alljournalentries:
                    alljournalentries.remove(indict[key])
                self.deserialized_items.sort(key = lambda x: x.entry_time, reverse=True)
                self.entry_time = self.deserialized_items[-1].entry_time
                if not self.is_open():
                    self.exit_time = max(self.deserialized_items, key = lambda x: x.exit_time).exit_time
            except:
                print("Error populating children:", key, "not found")
                continue
    
    def is_open(self):
        isopen = False
        if len(self.items) == 0:
            return True
        for je in self.deserialized_items:
            isopen |= je.is_open()
        return isopen

    def isidea(self):
        return False

    def is_group(self):
        return True

    def has_valid_entry_time(self):
        return self.entry_time != toIST_fromtimestamp(0)

    def has_valid_exit_time(self):
        return self.exit_time != toIST_fromtimestamp(0)

    def get_entry_time(self):
        return arrow.get(self.entry_time).humanize()

    def get_comment_count(self):
        return self.comment_count
    
    def get_item_count(self):
        return len(self.deserialized_items)

    def points_gain(self):
        sum = 0
        for je in self.deserialized_items:
            sum += je.points_gain()
        return sum

    def profit(self):
        sum = 0
        for je in self.deserialized_items:
            sum += je.profit()
        return sum

    def fetch_exit_price_as_ltp(self):
        for je in self.deserialized_items:
            je.fetch_exit_price_as_ltp()

    def get_category(self):
        category = set()
        now = IST_now().strftime("%b%y")
        if self.is_open():
            category = {'month'}
        if self.name.find(now) != -1:
            category = {'month'}
        if re.search(r"\bFY20\d\d\b", self.name):
            category = {'year'}
        return category

    def groupby(self, grouptype):
        if grouptype == 'symbol':
            group_func = lambda x: x.symbol
        elif grouptype == 'instrument':
            group_func = lambda x: x.tradingsymbol
        elif grouptype == 'strike':
            group_func = lambda x: stockutils.convert_from_zerodha_convention(x.tradingsymbol)[3]
        elif grouptype == 'expiry':
            group_func = lambda x: stockutils.convert_from_zerodha_convention(x.tradingsymbol)[1]
        else:
            return self

        entry_items = filter(lambda x: not x.is_group(), self.deserialized_items)
        group_items = filter(lambda x: x.is_group(), self.deserialized_items)
        jgnew = JournalEntryGroup(None, {})
        jgnew.name = self.name
        jgnew.deserialized_items.extend(group_items)
        for k,group in itertools.groupby(entry_items, group_func):
            jenew = functools.reduce(lambda a,b: a.reduce(b), group)
            jenew.tradingsymbol = k
            jenew.key = ''
            jgnew.deserialized_items.append(jenew)
        return jgnew


class JournalEntry(object):
    """Corresponds to one entry in trade journal"""
    def __init__(self, key, entity): 
        self.key = key
        self.symbol = entity['symbol'] if 'symbol' in entity.keys() else ''
        try:
            self.entry_time = toIST_fromtimestamp(float(entity['entry_time']))
        except:
            self.entry_time = toIST_fromtimestamp(0)
        try:
            self.exit_time = toIST_fromtimestamp(float(entity['exit_time'])) 
        except:
            self.exit_time = toIST_fromtimestamp(0)
        self.entry_price = entity['entry_price'] if 'entry_price' in entity.keys() else ''
        self.exit_price = entity['exit_price'] if 'exit_price' in entity.keys() else '' 
        self.quantity = entity['quantity'] if 'quantity' in entity.keys() else ''
        self.entry_sl = entity['entry_sl'] if 'entry_sl' in entity.keys() else ''
        self.entry_target = entity['entry_target'] if 'entry_target' in entity.keys() else ''
        self.direction = entity['direction'] if 'direction' in entity.keys() else ''
        self.rating = entity['rating'] if 'rating' in entity.keys() else ''
        self.strategy = entity['strategy'] if 'strategy' in entity.keys() and not not entity['strategy'] else 'default'
        self.timeframe = entity['timeframe'] if 'timeframe' in entity.keys() and not not entity['timeframe'] else '1d'
        self.is_idea = entity['is_idea'] if 'is_idea' in entity.keys() else ''
        self.tradingsymbol = entity['tradingsymbol'] if 'tradingsymbol' in entity.keys() and not not entity['tradingsymbol'] else ''
        self.position_changes = []
        self.comment_count = 0
        self.chart_count = 0
        self.points_gain_prop = None
        self.profit_prop = None
        self.quantity_prop = None
    
    def reduce(self, other):
        jenew = JournalEntry(None, {})
        jenew.entry_time = min(self.entry_time, other.entry_time)
        jenew.exit_time = toIST_fromtimestamp(0) if self.is_open() or other.is_open() else max(self.exit_time, other.exit_time)
        jenew.points_gain_prop = self.points_gain() + other.points_gain()
        jenew.profit_prop = self.profit()+ other.profit()
        jenew.quantity_prop = float(self.directionalqty()) + float(other.directionalqty())
        return jenew

    def fetch_exit_price_as_ltp(self):
        if self.is_open() and not self.exit_price:
            self.exit_price = stockutils.get_quote(self.tradingsymbol)

    def isidea(self):
        return self.is_idea == 'Y'
    
    def is_group(self):
        return False

    def is_open(self):
        return not self.has_valid_exit_time()

    def has_valid_entry_time(self):
        return self.entry_time != toIST_fromtimestamp(0)

    def has_valid_exit_time(self):
        return self.exit_time != toIST_fromtimestamp(0)

    def is_profitable(self):
        try:
            if not self.is_open():
                longprofitable = float(self.exit_price) >= float(self.entry_price)
                if self.direction == 'LONG':
                    return longprofitable
                else:
                    return not longprofitable
        except:
            return False

    def directionalqty(self):
        if self.quantity_prop:
            return str(self.quantity_prop)
        if self.direction == 'SHORT':
            return '-'+self.quantity
        else:
            return self.quantity

    def points_gain(self):
        if self.points_gain_prop:
            return self.points_gain_prop
        gain = 0
        try:
            if self.entry_price:
                gain = float(self.exit_price) - float(self.entry_price)
                if self.direction == 'SHORT':
                    gain = -gain
        except:
            pass
        return gain

    def profit(self):
        if self.profit_prop:
            return self.profit_prop
        profit = 0
        if self.entry_price and self.quantity:
            profit = float(self.quantity) * self.points_gain()
        return profit

    def get_entry_time(self):
        return arrow.get(self.entry_time).humanize()

    def is_aged(self, days):
        return (IST_now() - self.entry_time) >= timedelta(days=days)

    def get_timeframe(self):
        if not self.timeframe:
            return '2h'
        return self.timeframe

    def get_indicator(self):
        if not self.strategy or self.strategy == 'tkcross':
            return 'stochastic'
        else:
            return 'macd'

    def get_comment_count(self):
        return self.comment_count
    
    def get_chart_count(self):
        return self.chart_count

    def get_category(self):
        category = set()
        if self.isidea():
            category.add('idea')
        return category

    def get_tradingsymbol_forview(self):
        attrib = stockutils.convert_from_zerodha_convention(self.tradingsymbol)
        if len(attrib) > 1:
            if attrib[2] == "Fut":
                html = "%s %s %s" % (attrib[0], attrib[1].split('-')[1].upper(), attrib[2].upper())
            else:
                html = "%s %s<br/><small>%s</small>" % (attrib[0], str(attrib[3])+attrib[2], attrib[1]) 
        else:
            html = self.tradingsymbol
        return html


class JournalEntryNotFound(Exception):
    """Exception raised when a trade entry object couldn't be retrieved from
    the repository."""
    pass

class Comment(object):
    def __init__(self, key, entity): 
        self.key = key
        self.add_time = toIST_fromtimestamp(float(entity['add_time']))
        self.title = entity['title'] if 'title' in entity.keys() else ''
        self.text = entity['text'] if 'text' in entity.keys() else ''
        self.symbol = key.split('_')[0]

class Chart(object):
    def __init__(self, key, entity): 
        self.key = key
        self.add_time = toIST_fromtimestamp(float(entity['add_time']))
        self.title = entity['title'] if 'title' in entity.keys() else ''
        self.data = entity['data']
        self.relativeUrl = 'charts/' + entity['data']

class Trade(object):
    def __init__(self, key, entity): 
        self.key = key
        self.date = toIST_fromtimestamp(float(entity['RowKey']))
        self.type = entity['trade_type']
        self.price = entity['price']
        self.quantity = entity['quantity']
        self.tradingsymbol = entity['tradingsymbol']

class TradeSignal(object):
    def __init__(self, entity): 
        self.symbol = entity['symbol']
        self.signalreportdate, self.timeframe, self.strategy = entity['PartitionKey'].split('_')        
        self.timeframe = entity['PartitionKey'].split('_')[1]        
        self.strategy = entity['PartitionKey'].split('_')[2]        
        self.signaldate = entity['datetime']        
        self.score = entity['score'] 
        self.direction = entity['direction'] 
        self.entry_price  = entity['entry_price'] 
        self.entry_sl  = entity['entry_sl'] 
        self.entry_target  = entity['entry_target'] 
        self.lotsize = entity['lotsize']
        TF = {'daily':'1d', 'weekly':'1wk', 'intraday':'2h'}
        self.relativeUrl = '/charts/%s?tf=%s'%(self.symbol, TF[self.timeframe])

def _load_samples_json():
    """Loads polls from samples.json file."""
    samples_path = path.join(path.dirname(__file__), 'samples.json')
    with open(samples_path, 'r') as samples_file:
        return json.load(samples_file)
