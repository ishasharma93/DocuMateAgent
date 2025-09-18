import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class KeyVaultHelper:
    def __init__(self, vault_url: str):
        self.vault_url = vault_url
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

    def get_secret(self, secret_name: str) -> str:
        secret = self.client.get_secret(secret_name)
        return secret.value

# Usage example:
# vault_url = "https://<your-keyvault-name>.vault.azure.net/"
# kv_helper = KeyVaultHelper(vault_url)
# api_key = kv_helper.get_secret("AZURE_OPENAI_API_KEY")
