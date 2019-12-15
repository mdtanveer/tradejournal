"""
The flask application package.
"""

from flask import Flask
from authlib.integrations.flask_client import OAuth
from flask import url_for, render_template, session, redirect
import os
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from . import settings

app = Flask(__name__)
oauth = OAuth(app)

import tradejournal.views

app.secret_key = os.urandom(24)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, userinfo):
        self.id = userinfo['oid']
        self.name = userinfo['name']
        
    def __repr__(self):
        return "%d/%s" % (self.id, self.name)

oauth.register(
    name='microsoft',
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET,
    server_metadata_url='https://login.microsoftonline.com/%s/v2.0/.well-known/openid-configuration'%settings.TENANT_ID,
    client_kwargs={'scope': 'openid profile email'}
)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    redirect_uri = url_for('authorize', _external=True)
    token = oauth.microsoft.authorize_access_token(redirect_uri=redirect_uri)
    userinfo = oauth.microsoft.parse_id_token(token)
    user = User(userinfo)
    session['userinfo'] = userinfo
    login_user(user)
    return redirect('/')

# callback to reload the user object        
@login_manager.user_loader
def load_user(userid):
    return User(session['userinfo'])
