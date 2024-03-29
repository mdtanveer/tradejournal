"""
Factory for the different types of repositories.
"""

def create_repository(name, settings):
    """Creates a repository from its name and settings. The settings
    is a dictionary where the keys are different for every type of repository.
    See each repository for details on the required settings."""
    if name == 'azurestorage':
        from .azuretablestorage import Repository
    else:
        raise ValueError('Unknown repository.')

    return Repository(settings)
