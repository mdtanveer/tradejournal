"""
Settings for the polls application.

You can set values of REPOSITORY_NAME and REPOSITORY_SETTINGS in
environment variables, or set the default values in code here.
"""

from os import environ

REPOSITORY_NAME = environ.get('REPOSITORY_NAME', 'azurestorage')

if REPOSITORY_NAME == 'azurestorage':
    REPOSITORY_SETTINGS = {
        'STORAGE_NAME': environ.get('STORAGE_NAME', 'devstoreaccount1'),
        'CONNECTION_STRING' : environ.get('CONNECTION_STRING', 'AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;')
    }
elif REPOSITORY_NAME == 'memory':
    REPOSITORY_SETTINGS = {}
else:
    raise ValueError('Unknown repository.')

CLIENT_ID = environ.get('CLIENT_ID', '0c1a5774-f145-4566-b3ed-f9b7698fe818')
CLIENT_SECRET =  environ.get('CLIENT_SECRET', '=qjBXh4-iR:2HTSk2=8n1PjsMxk4AIo.')
TENANT_ID = environ.get('TENANT_ID', 'e290c7cd-29c5-4763-a016-cc1bf155224c')