import nsepython
import re
import calendar
from memoization import cached
import urllib
import jmespath
import requests
import json
from .tradejournalexceptions import ExpiryNotFoundException

#examples
# monthly expiry PE BANKNIFTY21SEP37500PE
# weekly expiry PE BANKNIFTY2192336700PE
# future KOTAKBANK21SEPFUT

@cached(ttl=7*24*3600)
def get_fnolist():
    return nsepython.fnolist()

def get_indices():
    return ["NIFTY", "BANKNIFTY", "CNXFINANCE", "MIDCPNIFTY", "CNXIT", "CNXAUTO", "CNXREALTY", "CNXINFRA", "CNXFMCG", "CNXENERGY", "CNXPHARMA" ]

@cached(ttl=7*24*3600)
def get_expiries_helper(symbol):
    payload = get_nse_quote(symbol)
    expiries = jmespath.search('stocks[?ends_with(metadata.instrumentType, `Futures`)].metadata.expiryDate', payload)
    return expiries

def get_expiries(symbol):
    if not symbol in ["BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY"]:
        symbol = "RELIANCE"
    return get_expiries_helper(symbol)

def get_expiry_day(symbol, year, month_abbr):
    expiries = get_expiries(symbol)
    for exp in expiries:
            if exp.endswith(f"{month_abbr}-{year}"):
                expiry_day = exp.split('-')[0]
                return expiry_day
    raise ExpiryNotFoundException(f"Couldn't find a valid expiry day for {year}-{month_abbr}, {symbol}")
        
def convert_from_zerodha_convention(name, expiry_fetch=True):
    name = str(name)
    try:
        # monthly expiry e.g. BANKNIFTY21SEP37500PE
        res = re.match(r"([A-Z\-&]+)(\d{2})([A-Z]{3})(\d+)([CP]E)", name)
        if res:
            symbol = res.group(1)
            year = res.group(2)
            month_abbr = res.group(3).title()
            strike = res.group(4)
            optionytype = res.group(5)
            if expiry_fetch:
                expiry_day = get_expiry_day(symbol, int("20"+year), month_abbr)
                expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
            else:
                expiry = month_abbr
            return (symbol, expiry, optionytype, int(strike))
        
        # weekly expiry PE BANKNIFTY2192336700PE BANKNIFTY24D2336700PE
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

        # future KOTAKBANK21SEPFUT
        res = re.match(r"([A-Z\-&]+)(\d{2})([A-Z]{3})FUT", name)
        if res:
            symbol = res.group(1)
            year = res.group(2)
            month_abbr = res.group(3).title()
            if expiry_fetch:
                expiry_day = get_expiry_day(symbol, int("20"+year), month_abbr)
                expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
            else:
                expiry = month_abbr
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
    except Exception as e:
        print("Error fetching quote", name, e)
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

@cached(ttl=3600)
def get_option_chain(symbol, expiry, ltp=None, count=0):
    if not symbol:
        return None
    option_chain = nsepython.option_chain(symbol)
    results = jmespath.search('records.data[*].{"expiry":expiryDate, "strike":strikePrice, "pe_ltp":PE.lastPrice, "ce_ltp":CE.lastPrice}', option_chain)
    if expiry:
        results = list(filter(lambda r: r["expiry"] == expiry, results))
    if ltp and count > 0:
        atm_index = 0
        for i, r in enumerate(results):
            if ltp-float(r["strike"]) < 0:
                atm_index = i
                break
        if atm_index-count >= 0 and atm_index+count < len(results):
            results = results[atm_index-count+1:atm_index+count]
    return results

@cached(ttl=30*24*3600)
def get_lot_size(symbol):
    #return nsepython.nse_get_fno_lot_sizes(symbol)
    lot_sizes = get_lot_sizes_dhan()
    return lot_sizes[symbol]

@cached(ttl=30*24*3600)
def get_lot_sizes_dhan():
    res = requests.post("https://open-web-scanx.dhan.co/scanx/allfut",
        json=json.loads('{"Data":{"Seg":2,"Instrument":"FUT","Count":200,"Page_no":1,"ExpCode":-1}}'),
        headers={
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Origin": "https://dhan.co",
            "Referer": "https://dhan.co/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "TE": "trailers",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "content-type": "application/json; charset=UTF-8"
        },
        cookies={},
        auth=(),
    )
    lots = jmespath.search("data.list[*].[sym, fo_dt[0].lot_type]", res.json())
    result = {x[0]:int(x[1].split()[0]) for x in lots}
    return result


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


    

