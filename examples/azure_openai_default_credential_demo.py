from azure.identity import DefaultAzureCredential
from azure.ai.openai import OpenAIClient
import os

# Get endpoint and deployment info from environment
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Authenticate using DefaultAzureCredential
credential = DefaultAzureCredential()
client = OpenAIClient(endpoint=endpoint, credential=credential)

# Example: Chat completion request
response = client.chat_completions.create(
    deployment_id=deployment_name,
    messages=[{"role": "user", "content": "Hello!"}],
    api_version=api_version
)

print(response.choices[0].message.content)
