import nsepython
import re
from nsepy.derivatives import get_expiry_date
import calendar
from filecache import filecache
import urllib
import jmespath

#examples
# monthly expiry PE BANKNIFTY21SEP37500PE
# weekly expiry PE BANKNIFTY2192336700PE
# future KOTAKBANK21SEPFUT

@filecache(900)
def get_expiry_day(year, month_abbr):
    try:
        expiry_day = list(get_expiry_date(year=year, 
            month=list(calendar.month_abbr).index(month_abbr), 
            index=False, stock=True))[0].day
    except:
        current_expiry = nsepython.expiry_list('RELIANCE')[0]
        expiry_day = current_expiry.split('-')[0]
    return expiry_day

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
            expiry_day = get_expiry_day(int("20"+year), month_abbr)
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
            expiry_day = get_expiry_day(int("20"+year), month_abbr)
            expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
            return (symbol, expiry, "Fut")
        return (name,)
    except:
        raise

@filecache(900)
def get_derivative_data(symbol):
    symbol = nsepython.nsesymbolpurify(symbol)
    payload = nsepython.nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
    return payload

def get_quote(name):
    try:
        args = convert_from_zerodha_convention(name)
        if len(args) == 3:
            return get_quote_future(*args)
        elif len(args) == 4:
            return get_quote_option(*args)
    except:
        return 0

def get_quote_future(symbol, expiry, optiontype):
    derivative_data = get_derivative_data(symbol)
    query_string = f'stocks[?metadata.expiryDate == `{expiry}` && metadata.optionType==`-`].metadata.lastPrice'
    return jmespath.search(query_string, derivative_data)[0]

def get_quote_option(symbol, expiry, optiontype, strike):
    derivative_data = get_derivative_data(symbol)
    optiontype = {'CE':'Call', 'PE':'Put'}[optiontype]
    query_string = f'stocks[?metadata.strikePrice == `{strike}` && metadata.expiryDate == `{expiry}` && metadata.optionType==`{optiontype}`].metadata.lastPrice'
    return jmespath.search(query_string, derivative_data)[0]

@filecache(900)
def get_quote_old(name):
    args = convert_from_zerodha_convention(name)
    print(args)
    try:
        return nsepython.nse_quote_ltp(*args)
    except:
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


    

