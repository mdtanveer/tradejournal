"""
Settings for the polls application.

You can set values of REPOSITORY_NAME and REPOSITORY_SETTINGS in
environment variables, or set the default values in code here.
"""

from os import environ

REPOSITORY_NAME = environ.get('REPOSITORY_NAME', 'azurestorage')

if REPOSITORY_NAME == 'azurestorage':
    REPOSITORY_SETTINGS = {
        'STORAGE_NAME': environ.get('STORAGE_NAME', ''),
        'CONNECTION_STRING' : environ.get('CONNECTION_STRING', '')
    }
elif REPOSITORY_NAME == 'memory':
    REPOSITORY_SETTINGS = {}
else:
    raise ValueError('Unknown repository.')

CLIENT_ID = environ.get('CLIENT_ID', '')
CLIENT_SECRET =  environ.get('CLIENT_SECRET', '')
TENANT_ID = environ.get('TENANT_ID', '')

HTTP_SCHEME = environ.get('HTTP_SCHEME', 'https')