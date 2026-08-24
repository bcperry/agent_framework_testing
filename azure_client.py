"""Azure OpenAI client factory.

Azure Government needs two things the framework won't infer:
  1. `DefaultAzureCredential(authority=AzureAuthorityHosts.AZURE_GOVERNMENT)`
  2. the Gov token scope -- agent-framework hardcodes the commercial
     `https://cognitiveservices.azure.com/.default`, so we build the bearer token
     provider ourselves and pass it as `credential` (callables are used as-is).
"""

import os

from agent_framework.openai import OpenAIChatClient
from azure.identity import (
    AzureAuthorityHosts,
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from dotenv import load_dotenv

load_dotenv()

GOV_ENDPOINT_SUFFIX = ".azure.us"
GOV_SCOPE = "https://cognitiveservices.azure.us/.default"
PUBLIC_SCOPE = "https://cognitiveservices.azure.com/.default"


def create_chat_client(**kwargs) -> OpenAIChatClient:
    """Build an OpenAIChatClient for Azure OpenAI, using Entra ID when no key is set."""
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return OpenAIChatClient(**kwargs)

    if GOV_ENDPOINT_SUFFIX in os.getenv("AZURE_OPENAI_ENDPOINT", ""):
        credential = DefaultAzureCredential(
            authority=AzureAuthorityHosts.AZURE_GOVERNMENT
        )
        scope = GOV_SCOPE
    else:
        credential = DefaultAzureCredential()
        scope = PUBLIC_SCOPE

    return OpenAIChatClient(
        credential=get_bearer_token_provider(credential, scope), **kwargs
    )
