import nsepython
import re
import calendar
from memoization import cached
import urllib
import jmespath

#examples
# monthly expiry PE BANKNIFTY21SEP37500PE
# weekly expiry PE BANKNIFTY2192336700PE
# future KOTAKBANK21SEPFUT

@cached(ttl=7*24*3600)
def get_expiry_day(symbol, year, month_abbr):
    payload = get_nse_quote(symbol)
    monthly_expiries = jmespath.search('stocks[?ends_with(metadata.instrumentType, `Futures`)].metadata.expiryDate', payload)
    for exp in monthly_expiries:
            if exp.endswith(f"{month_abbr}-{year}"):
                expiry_day = exp.split('-')[0]
                return expiry_day
    raise Exception(f"Couldn't find a valid expiry day for {year}-{month_abbr}, {symbol}")
        
def convert_from_zerodha_convention(name):
    name = str(name)
    try:
        res = re.match(r"([A-Z\-&]+)(\d{2})([A-Z]{3})(\d+)([CP]E)", name)
        if res:
            symbol = res.group(1)
            year = res.group(2)
            month_abbr = res.group(3).title()
            strike = res.group(4)
            optionytype = res.group(5)
            expiry_day = get_expiry_day(symbol, int("20"+year), month_abbr)
            expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
            return (symbol, expiry, optionytype, int(strike))
        
        res = re.match(r"([A-Z\-&]+)(\d{2})([\dOND])(\d{2})(\d+)([CP]E)", name)
        if res:
            symbol = res.group(1)
            year = res.group(2)
            monthcode = res.group(3)
            weekdate = res.group(4)
            strike = res.group(5)
            optionytype = res.group(6)
            if monthcode.isnumeric():
                month_abbr = calendar.month_abbr[int(monthcode)]
            else:
                codes = {'O':'Oct', 'N':'Nov', 'D':'Dec'}
                month_abbr = codes[monthcode]
            expiry = weekdate + '-' + month_abbr + '-20' + year
            return (symbol, expiry, optionytype, int(strike))

        res = re.match(r"([A-Z\-&]+)(\d{2})([A-Z]{3})FUT", name)
        if res:
            symbol = res.group(1)
            year = res.group(2)
            month_abbr = res.group(3).title()
            expiry_day = get_expiry_day(symbol, int("20"+year), month_abbr)
            expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
            return (symbol, expiry, "Fut")
        return (name,)
    except:
        raise

@cached(ttl=900)
def get_nse_quote(symbol):
    return nsepython.nse_quote(symbol)

def cache_clear():
    get_nse_quote.cache_clear()

async def get_quote(name):
    try:
        args = convert_from_zerodha_convention(name)
        if len(args) == 3:
            return get_quote_future(*args)
        elif len(args) == 4:
            return get_quote_option(*args)
        elif len(args) == 1:
            return get_quote_spot(*args)
    except:
        return 0

@cached(ttl=12*3600)
def get_india_vix():
    return nsepython.indiavix()

def get_quote_future(symbol, expiry, optiontype):
    derivative_data = get_nse_quote(symbol)
    query_string = f'stocks[?metadata.expiryDate == `{expiry}` && metadata.optionType==`-`].metadata.lastPrice'
    return jmespath.search(query_string, derivative_data)[0]

def get_quote_option(symbol, expiry, optiontype, strike):
    derivative_data = get_nse_quote(symbol)
    optiontype = {'CE':'Call', 'PE':'Put'}[optiontype]
    query_string = f'stocks[?metadata.strikePrice == `{strike}` && metadata.expiryDate == `{expiry}` && metadata.optionType==`{optiontype}`].metadata.lastPrice'
    return jmespath.search(query_string, derivative_data)[0]

def get_quote_spot(symbol):
    payload = get_nse_quote(symbol)
    return payload["underlyingValue"]

@cached(ttl=900)
def get_quote_old(name):
    args = convert_from_zerodha_convention(name)
    try:
        return nsepython.nse_quote_ltp(*args)
    except:
        print("Error fetching:", args)
        return 0

def test():
    me = "BANKNIFTY21SEP37500PE"
    we = "BANKNIFTY21O0736700PE"
    mf = "KOTAKBANK21SEPFUT"

    print(convert_from_zerodha_convention(me))
    print(convert_from_zerodha_convention(we))
    print(convert_from_zerodha_convention(mf))

def test2():
    me = "BANKNIFTY21OCT37600CE"
    we = "BANKNIFTY21O1436700PE"
    mf = "KOTAKBANK21OCTFUT"

    print(get_quote(me))
    print(get_quote(we))
    print(get_quote(mf))

def test3():
    o = "M&M21OCT880CE"
    print(get_quote(o))

if __name__ == "__main__":
    test2()


    

