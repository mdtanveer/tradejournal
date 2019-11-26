"""
Settings for the polls application.

You can set values of REPOSITORY_NAME and REPOSITORY_SETTINGS in
environment variables, or set the default values in code here.
"""

from os import environ

REPOSITORY_NAME = environ.get('REPOSITORY_NAME', 'azuretablestorage')

if REPOSITORY_NAME == 'azuretablestorage':
    REPOSITORY_SETTINGS = {
        'STORAGE_NAME': environ.get('STORAGE_NAME', 'tradejournalstorage'),
        'STORAGE_KEY': environ.get('STORAGE_KEY', '0YGfSMwBb4xJaMDQ6fr2jjNRRd3aqYCvlqDdwvhul4uCihGufJzHXXq0M5Db5tB/veW1cW3/TthwqMcpPreMwg=='),
    }
elif REPOSITORY_NAME == 'memory':
    REPOSITORY_SETTINGS = {}
else:
    raise ValueError('Unknown repository.')
