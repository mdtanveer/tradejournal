from . import azurekeyvault
import requests

class PositionMixin:
    def get_position_data(self, groupby='itype'):
        TIMEOUT=3
        if not self.kvclient:
            self.kvclient = azurekeyvault.AzureKeyVaultClient()
            self.kvclient.fetch_secrets()

        data_found = False
        if self.session:
            z = self.session.get("https://kite.zerodha.com/oms/portfolio/positions", timeout=TIMEOUT)
            data_found = (z.status_code == 200)
        if not data_found:
            self.session = requests.Session()
            x = self.session.post("https://kite.zerodha.com/api/login", 
                                  data = {'user_id': self.kvclient.get_secret('zerodha-login'), 
                                          'password': self.kvclient.get_secret('zerodha-password')}, timeout=TIMEOUT)
            res = x.json()
            tfd = res['data']
            del(tfd['twofa_type'])
            del(tfd['twofa_status'])
            tfd['twofa_value'] = self.kvclient.get_secret('zerodha-pin')
            y = self.session.post("https://kite.zerodha.com/api/twofa", data = tfd, timeout=TIMEOUT)
            self.session.headers.update({'Authorization': 'enctoken '+y.cookies['enctoken']})
            z = self.session.get("https://kite.zerodha.com/oms/portfolio/positions", timeout=TIMEOUT)
        data = z.json()['data']['net']
        df = pd.DataFrame(data)
        COLUMNS = ['tradingsymbol', 'unrealised', 'quantity', 'average_price', 'last_price', ]
        df = df[COLUMNS]
        df['symbol'] = df['tradingsymbol'].apply(get_symbol)
        df['itype'] = df['tradingsymbol'].apply(get_inst_type)

        trades = self.get_journalentries_helper(lambda x:x, 60)
        tdf = pd.DataFrame(trades)
        tdf = tdf.query('(exit_time =="0" | exit_time == "") & is_idea !="Y"')
        tdf = tdf[['symbol','strategy', 'timeframe', 'tradingsymbol']]

        out = df.merge(tdf, left_on=['symbol', 'tradingsymbol'], right_on=['symbol', 'tradingsymbol'], how='left')
        out['strategy'] = out['strategy'].fillna('default')
        groupby = groupby if groupby in out.columns else 'itype'
        grp = out.groupby(groupby)

        position_data = []
        for groupname in grp.groups.keys():
            cols = list(COLUMNS)
            df = grp.get_group(groupname)[cols]
            meta = {
                'name': groupname,
                'count' : df.shape[0],
                'unrealised_tot': round(df['unrealised'].sum(), 2)
                }

            position_data.append((meta, df.apply(lambda x: x.to_dict(), axis=1)))
        grand_total = round(out['unrealised'].sum(), 2)

        return (position_data, grand_total)
