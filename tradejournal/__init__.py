"""
The flask application package.
"""

from flask import Flask
from flask import url_for, render_template, session, redirect
import os

def create_app():
    app = Flask(__name__)

    app.secret_key = os.urandom(24)

    with app.app_context():
        import tradejournal.oauth
        import tradejournal.views

        from tradejournal.plotlydash.dashboard import create_dashboard
        app = create_dashboard(app)

    return app

