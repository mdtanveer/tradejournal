"""
This script runs the tradejournal application using a development server.
"""

from os import environ

from tradejournal import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST','localhost')
    try:
        PORT = 5555 #int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
