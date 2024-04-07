from . import azurekeyvault
import requests
import pandas as pd
import tempfile, os, pickle
from jugaad_trader import Zerodha
from . import tradejournalutils as tju

class PositionMixin:
    def __init__(self):
        self.kite = Zerodha()
        self.session_file_dir = tempfile.gettempdir()
        self.session_file_path = os.path.join(tempfile.gettempdir(), ".zsession")

    def try_login_zerodha(self):
        self.kite.load_session(self.session_file_path)
        p = self.kite.profile()
        return p

    def login_zerodha_step1(self, user_id, password):
        self.kite.user_id = user_id
        self.kite.password = password
        j = self.kite.login_step1()
        if j['status'] == 'error':
            raise Exception("Error: {}".format(j['message']))
        return j
        
    def login_zerodha_step2(self, twofa, prevstep):
        self.kite.twofa = twofa
        j = self.kite.login_step2(prevstep)
        if j['status'] == 'error':
            raise Exception("Error: {}".format(j['message']))

        self.kite.enc_token = self.kite.r.cookies['enctoken']
        p = self.kite.profile()

        with open(self.session_file_path, "wb") as fp:
            pickle.dump(self.kite.reqsession, fp)
        return p['user_name']
        

    def get_position_data_response(self, groupby):
        # Set access token loads the stored session.
        data = self.kite.positions()['net']
        return data

    def get_position_data_response_old(self, groupby):
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
            return data

    def get_position_data(self, groupby='itype'):
        data = self.get_position_data_response(groupby)
        df = pd.DataFrame(data)
        COLUMNS = ['tradingsymbol', 'unrealised', 'quantity', 'average_price', 'last_price', ]
        df = df[COLUMNS]
        df['symbol'] = df['tradingsymbol'].apply(tju.get_symbol)
        df['itype'] = df['tradingsymbol'].apply(tju.get_inst_type)

        trades = self.get_journalentries_helper(lambda x:x, 60)
        tdf = pd.DataFrame(trades)
        if not tdf.empty:
            tdf = tdf.query('(exit_time =="0" | exit_time == "") & is_idea !="Y"')
            tdf = tdf[['symbol','strategy', 'timeframe', 'tradingsymbol']]

            out = df.merge(tdf, left_on=['symbol', 'tradingsymbol'], right_on=['symbol', 'tradingsymbol'], how='left')
        else:
            out = df
            out["strategy"] = ""
            out["timeframe"] = ""
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
