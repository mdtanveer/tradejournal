import nsepython as nse
import re
from nsepy.derivatives import get_expiry_date
import calendar
from filecache import filecache

#examples
# monthly expiry PE BANKNIFTY21SEP37500PE
# weekly expiry PE BANKNIFTY2192336700PE
# future KOTAKBANK21SEPFUT

def convert_from_zerodha_convention(name):
    res = re.match("([A-Z\-&]+)(\d{2})([A-Z]{3})(\d+)([CP]E)", name)
    if res:
        symbol = res.group(1)
        year = res.group(2)
        month_abbr = res.group(3).title()
        strike = res.group(4)
        optionytype = res.group(5)
        expiry_day = list(get_expiry_date(year=int("20"+year), month=list(calendar.month_abbr).index(month_abbr), index=False, stock=True))[0].day
        expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
        return (symbol, expiry, optionytype, int(strike))
    
    res = re.match("([A-Z\-&]+)(\d{2})([\dOND])(\d{2})(\d+)([CP]E)", name)
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

    res = re.match("([A-Z\-&]+)(\d{2})([A-Z]{3})FUT", name)
    if res:
        symbol = res.group(1)
        year = res.group(2)
        month_abbr = res.group(3).title()
        expiry_day = list(get_expiry_date(year=int("20"+year), month=list(calendar.month_abbr).index(month_abbr), index=False, stock=True))[0].day
        expiry = str(expiry_day)+'-'+month_abbr+'-20'+year
        return (symbol, expiry, "Fut")

    return None

@filecache(900)
def get_quote(name):
    args = convert_from_zerodha_convention(name)
    try:
        return nse.nse_quote_ltp(*args)
    except:
        return ''

def test():
    me = "BANKNIFTY21SEP37500PE"
    we = "BANKNIFTY21O0736700PE"
    mf = "KOTAKBANK21SEPFUT"

    print(convert_from_zerodha_convention(me))
    print(convert_from_zerodha_convention(we))
    print(convert_from_zerodha_convention(mf))

def test2():
    me = "BANKNIFTY21SEP37500PE"
    we = "BANKNIFTY21O0736700PE"
    mf = "KOTAKBANK21SEPFUT"

    print(get_quote(me))
    print(get_quote(we))
    print(get_quote(mf))

if __name__ == "__main__":
    test2()


    
