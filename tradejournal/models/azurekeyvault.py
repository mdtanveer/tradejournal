from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

class AzureKeyVaultClient():
    def __init__(self):
        credential = DefaultAzureCredential()
        keyvaultname = os.environ['AZURE_KEYVAULT_NAME']
        self.secret_client = SecretClient(vault_url=f"https://{keyvaultname}.vault.azure.net/", credential=credential)
        self.SECRET_KEYS=["zerodha-login", "zerodha-password", "zerodha-pin", "last-trade-sync-date"]
        self.secrets={}
    
    def fetch_secrets(self):
        for key in self.SECRET_KEYS:
            self.secrets[key] = self.secret_client.get_secret(key).value

    def get_secret(self, key):
        return self.secrets[key]
