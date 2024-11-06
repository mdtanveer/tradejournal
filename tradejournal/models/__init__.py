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
from optionlab import Inputs, run_strategy
from memoization import cached
import asyncio
import plotly
import plotly.express as px
from .tradejournalexceptions import ExpiryNotFoundException
import numpy as np

DAYSHIFT=5

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
        except Exception as e:
            self.entry_time = toIST_fromtimestamp(0)
        try:
            self.exit_time = toIST_fromtimestamp(float(entity['exit_time']))
        except Exception as e:
            self.exit_time = toIST_fromtimestamp(0)
        self.rating = entity['rating'] if 'rating' in entity.keys() else ''
        self.strategy = entity['strategy'] if 'strategy' in entity.keys() and not not entity['strategy'] else 'default'
        self.comment_count = 0
        self.name = entity['name'] if 'name' in entity.keys() else ''
        self.items = entity["items"] if 'items' in entity.keys() else ''
        self.deserialized_items = []
        self.is_virtual = False

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
            except Exception as e:
                print("Error populating children:", key, "not found: ", e)
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

    def entry_cost(self):
        sum = 0
        for je in self.deserialized_items:
            sum += je.entry_cost
        return sum
    
    def exit_cost(self):
        sum = 0
        for je in self.deserialized_items:
            sum += je.exit_cost
        return sum

    def profit_percent(self):
        if self.entry_cost() != 0:
            return self.profit()/self.entry_cost()*100
        else:
            return 0

    def profit(self):
        sum = 0
        for je in self.deserialized_items:
            sum += je.profit()
        return sum

    async def fetch_exit_price_as_ltp(self, force_refresh):
        async with asyncio.TaskGroup() as tg:
            for je in self.deserialized_items:
                tg.create_task(je.fetch_exit_price_as_ltp(force_refresh))

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
        groupview_translate_func = lambda x: x
        if grouptype == 'symbol':
            group_func = lambda x: x.symbol
        elif grouptype == 'instrument':
            group_func = lambda x: x.tradingsymbol
        elif grouptype == 'strike':
            group_func = lambda x: stockutils.convert_from_zerodha_convention(x.tradingsymbol, False)[3]
        elif grouptype == 'expiry':
            group_func = lambda x: stockutils.convert_from_zerodha_convention(x.tradingsymbol, False)[1]
        elif grouptype == 'status':
            group_func = lambda x: x.is_open()
            groupview_translate_func = lambda n: "Realized" if not n else "Unrealized"
        elif grouptype == 'symbolandentry':
            group_func = lambda x: str(x.entry_time.date()) + ': ' + x.symbol 
        elif grouptype == 'symbolandexpiry':
            group_func = lambda x: stockutils.convert_from_zerodha_convention(x.tradingsymbol, False)[1] + ': ' + x.symbol 
        else:
            return self

        entry_items = filter(lambda x: not x.is_group(), self.deserialized_items)
        group_items = filter(lambda x: x.is_group(), self.deserialized_items)
        jgnew = JournalEntryGroup(None, {})
        jgnew.name = self.name
        jgnew.deserialized_items.extend(group_items)
        jgnew.is_virtual = True
        for k,group in itertools.groupby(sorted(entry_items, key=group_func), group_func):
            jeaccum = JournalEntry(None, {})
            jeaccum.entry_time = None
            jeaccum.exit_time = None
            jenew = functools.reduce(lambda a,b: a.reduce(b), group, jeaccum)
            jenew.tradingsymbol = groupview_translate_func(k)
            jenew.key = ''
            jgnew.deserialized_items.append(jenew)
        return jgnew

    def option_premium(self):
        premium = 0
        for je in self.deserialized_items:
            if not je.is_group():
                try:
                    premium += je.option_premium()
                except TypeError as err:
                    continue
        return premium

    def get_optionlab_strategy(self):
        legs = []
        underlying = None
        expiry = None
        entry_date = None
        open_items = list(filter(lambda x: x.is_open(), self.deserialized_items))
        closed_items = list(filter(lambda x: not x.is_open(), self.deserialized_items))
        
        override_closed = False

        if len(open_items) == 0 and len(closed_items) > 0:
            print("Overriding closed items as open for analysis")
            open_items = closed_items
            closed_items = []
            override_closed = True

        if len(open_items) == 0:
            raise Exception("No trades as input")

        for je in open_items:
            if not je.is_group():
                leg = je.get_optionlab_strategy(override_closed)
                print(leg)
                if not underlying:
                    underlying = leg['symbol']
                else:
                    if leg['symbol'] != underlying:
                        raise TypeError("Non-homogeneous symbol found")
                if not expiry:
                    expiry = leg['expiry']
                else:
                    if leg['expiry'] != expiry:
                        raise TypeError("Non-homogeneous expiry found")
                legs.append(leg['strategy'])

        closed_leg = {'type': 'closed', 'prev_pos': 0}
        for je in closed_items:
            if not je.is_group():
                closed_leg['prev_pos'] += je.profit()

        if closed_leg['prev_pos'] > 0:
            legs.append(closed_leg)

        if underlying == None:
            raise Exception("Invalid symbol1")

        model =  {'symbol': underlying, 'expiry': expiry, 'legs': legs}
        return model

    async def get_optionlab_result_async(self):
        return self.get_optionlab_result()

    @cached(ttl=3600)
    def get_optionlab_result(self):
        model = self.get_optionlab_strategy()
        spot_price = stockutils.get_quote_spot(model['symbol'])
        strikes = [stockutils.convert_from_zerodha_convention(x.tradingsymbol, False)[3] for x in self.deserialized_items]
        strikes_avg = spot_price

        if len(strikes) > 0:
            strikes_avg = sum(strikes)/len(strikes)

        target_date = np.busday_offset(datetime.now().date(), 0, roll="backward").astype(datetime)
        start_date = np.busday_offset(target_date, -DAYSHIFT, roll="forward").astype(datetime)
        if model['expiry']:
            start_date = np.busday_offset(datetime.now().date(), 0, roll="backward").astype(datetime)
            target_date = model['expiry']
        else:
            spot_price = strikes_avg

        inputs_data = {
            "stock_price": spot_price, 
            "start_date": start_date,
            "target_date": target_date,
            "volatility": stockutils.get_india_vix()/100,
            "interest_rate": 0.0002,
            "min_stock": round(strikes_avg * 0.94, 2),
            "max_stock": round(strikes_avg * 1.06, 2),
            "strategy": model['legs'],
            "mc_prices_number": 100
            }

        print(inputs_data)

        inputs = Inputs.model_validate(inputs_data)
        out = run_strategy(inputs)

        size = len(out.data.stock_price_array)
        k = int(size/500)
        fig = px.line(x=out.data.stock_price_array[:-k:k], y=out.data.strategy_profit[:-k:k])
        fig.add_vline(spot_price, line_dash="dash", line_color="gray")
        fig.add_hline(0)
        graph = fig.to_html(full_html = False, include_plotlyjs ='cdn')

        return out, graph


class JournalEntry(object):
    """Corresponds to one entry in trade journal"""
    def __init__(self, key, entity): 
        self.key = key
        self.symbol = entity['symbol'] if 'symbol' in entity.keys() else ''
        try:
            self.entry_time = toIST_fromtimestamp(float(entity['entry_time']))
        except Exception as e:
            self.entry_time = toIST_fromtimestamp(0)
        try:
            self.exit_time = toIST_fromtimestamp(float(entity['exit_time'])) 
        except Exception as e:
            self.exit_time = toIST_fromtimestamp(0)
        self.entry_price = entity['entry_price'] if 'entry_price' in entity.keys() else 0
        self.exit_price = entity['exit_price'] if 'exit_price' in entity.keys() else 0
        self.quantity = entity['quantity'] if 'quantity' in entity.keys() else 0
        self.entry_sl = entity['entry_sl'] if 'entry_sl' in entity.keys() else 0
        self.entry_target = entity['entry_target'] if 'entry_target' in entity.keys() else 0
        self.direction = entity['direction'] if 'direction' in entity.keys() else ''
        self.rating = entity['rating'] if 'rating' in entity.keys() else ''
        self.strategy = entity['strategy'] if 'strategy' in entity.keys() and not not entity['strategy'] else 'default'
        self.timeframe = entity['timeframe'] if 'timeframe' in entity.keys() and not not entity['timeframe'] else '2h'
        self.is_idea = entity['is_idea'] if 'is_idea' in entity.keys() else ''
        self.tradingsymbol = entity['tradingsymbol'] if 'tradingsymbol' in entity.keys() and not not entity['tradingsymbol'] else ''
        self.position_changes = []
        self.comment_count = 0
        self.chart_count = 0
        self.points_gain_prop = None
        self.profit_prop = None
        self.quantity_prop = None
        self.entry_cost = 0
        self.exit_cost = 0
    
    def reduce(self, other):
        jenew = JournalEntry(None, {})
        if self.entry_time == None:
            jenew.entry_time = other.entry_time
        else:
            jenew.entry_time = min(self.entry_time, other.entry_time) if other.has_valid_entry_time() else self.entry_time
        if self.exit_time == None:
            jenew.exit_time = other.exit_time
        else:
            jenew.exit_time = toIST_fromtimestamp(0) if self.is_open() or other.is_open() else max(self.exit_time, other.exit_time)
        jenew.points_gain_prop = self.points_gain() + other.points_gain()
        jenew.profit_prop = self.profit()+ other.profit()
        jenew.quantity_prop = float(self.directionalqty()) + float(other.directionalqty())
        jenew.entry_cost = float(self.entry_cost)+float(other.entry_price)*float(other.directionalqty())
        jenew.exit_cost = float(self.exit_cost)+float(other.exit_price)*float(other.directionalqty())
        return jenew

    async def fetch_exit_price_as_ltp(self, force_refresh):
        if force_refresh == 1:
            stockutils.cache_clear()
        if self.is_open():
            self.exit_price = await stockutils.get_quote(self.tradingsymbol)

    def isidea(self):
        return self.is_idea == 'Y'
    
    def is_group(self):
        return False

    def is_open(self):
        return not self.has_valid_exit_time()

    def has_valid_entry_time(self):
        return self.entry_time != toIST_fromtimestamp(0)

    def has_valid_exit_time(self):
        return self.exit_time != None and self.exit_time != toIST_fromtimestamp(0)

    def is_profitable(self):
        try:
            if not self.is_open():
                longprofitable = float(self.exit_price) >= float(self.entry_price)
                if self.direction == 'LONG':
                    return longprofitable
                else:
                    return not longprofitable
        except Exception as e:
            print(e)
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
        except Exception as e:
            print(e)

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

    def get_tradingsymbol_forview(self, expiry_fetch=True):
        try:
            attrib = stockutils.convert_from_zerodha_convention(self.tradingsymbol, expiry_fetch)
        except Exception as e:
            print(e)

            if expiry_fetch == True:
                expiry_fetch = False
                attrib = stockutils.convert_from_zerodha_convention(self.tradingsymbol, expiry_fetch)

        if len(attrib) > 1:
            if attrib[2] == "Fut":
                if expiry_fetch:
                    html = "%s %s %s" % (attrib[0], attrib[1].split('-')[1].upper(), attrib[2].upper())
                else:
                    html = "%s %s %s" % (attrib[0], attrib[1].upper(), attrib[2].upper())
            else:
                if expiry_fetch:
                    html = "%s %s<br/><small>%s</small>" % (attrib[0], str(attrib[3])+attrib[2], attrib[1]) 
                else:
                    html = "%s %s %s %s" % (attrib[0], attrib[1].upper(), str(attrib[3]), attrib[2]) 
        else:
            html = self.tradingsymbol
        return html

    def is_option(self):
        attrib = stockutils.convert_from_zerodha_convention(self.tradingsymbol, False)
        return len(attrib) == 4

    def option_premium(self):
        if not self.is_option():
            raise TypeError("Premium is not defined for non-options")
        premium = float(self.entry_price) * float(self.quantity)
        if self.direction == 'LONG':
            premium = -premium
        return premium

    def get_optionlab_strategy(self, override_closed = False):
        if self.is_option():
            expiry_valid = True
            try:
                symbol, expiry, optionytype, strike = stockutils.convert_from_zerodha_convention(self.tradingsymbol)
                expiry = datetime.strptime(expiry, "%d-%b-%Y").date()
                if datetime.now().date() >= expiry:
                    expiry_valid = False
            except ExpiryNotFoundException:
                symbol, expiry, optionytype, strike = stockutils.convert_from_zerodha_convention(self.tradingsymbol, False)
                expiry_valid = False

            days_to_expiry = DAYSHIFT
            if expiry_valid:
                start_date = np.busday_offset(datetime.now().date(), 0, roll="backward").astype(datetime)
                days_to_expiry = np.busday_count(start_date, expiry)
            else:
                expiry = None

            if override_closed or self.is_open():
                result =  {
                        'symbol' : symbol,
                        'expiry' : expiry,
                        'entry_date' : self.entry_time.date(),
                        'strategy': {
                            "type": "put" if optionytype == "PE" else "call",
                            "strike": strike,
                            "premium": float(self.entry_price),
                            "n": float(self.quantity),
                            "action":"buy" if self.direction == 'LONG' else "sell",
                            "expiration": days_to_expiry
                            }
                        }
                return result
            elif not override_closed:
                result =  {
                        'symbol' : symbol,
                        'expiry' : expiry,
                        'entry_date' : self.entry_time.date(),
                        'strategy': {
                            "type": "closed",
                            "prev_pos": self.profit()
                            }
                        }
                return result
        raise TypeError("Not an option or trade is closed")

    def profit_percent(self):
        return self.profit()/self.entry_cost*100 if self.entry_cost != 0 else 0


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
        self.symbol = key.rsplit('_', 1)[0]
        self.badge = ""

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
