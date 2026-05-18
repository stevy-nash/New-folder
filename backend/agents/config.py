import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.keyvault.secrets import SecretClient

load_dotenv()


@dataclass
class Config:
    # --- Azure AI Foundry / OpenAI ---
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5")
    azure_openai_embedding_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

    # --- Azure Cosmos DB (NoSQL API) ---
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "")
    cosmos_database: str = os.getenv("COSMOS_DATABASE", "retrodoc")
    cosmos_vectors_container: str = os.getenv("COSMOS_VECTORS_CONTAINER", "vectors")
    cosmos_sessions_container: str = os.getenv("COSMOS_SESSIONS_CONTAINER", "sessions")
    cosmos_benchmark_container: str = os.getenv("COSMOS_BENCHMARK_CONTAINER", "benchmark_results")
    cosmos_vector_index_type: str = os.getenv("COSMOS_VECTOR_INDEX_TYPE", "quantizedFlat")

    # --- Azure Key Vault ---
    keyvault_url: str = os.getenv("KEYVAULT_URL", "")
    keyvault_cosmos_secret: str = os.getenv("KEYVAULT_COSMOS_SECRET", "cosmos-key")

    # --- Azure Blob Storage ---
    azure_storage_account: str = os.getenv("AZURE_STORAGE_ACCOUNT", "subsiarecs")
    azure_storage_key: str = os.getenv("AZURE_STORAGE_KEY", "")
    azure_storage_container: str = os.getenv("AZURE_STORAGE_CONTAINER", "documents")

    # --- Azure Document Intelligence ---
    azure_doc_intelligence_endpoint: str = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT", "")
    azure_doc_intelligence_key: str = os.getenv("AZURE_DOC_INTELLIGENCE_KEY", "")


config = Config()


@lru_cache(maxsize=1)
def _get_cosmos_secret_from_vault() -> str:
    """Fetch the Cosmos DB connection string from Key Vault. Cached for the process lifetime."""
    vault_client = SecretClient(vault_url=config.keyvault_url, credential=DefaultAzureCredential())
    return vault_client.get_secret(config.keyvault_cosmos_secret).value


def get_cosmos_client() -> "CosmosClient":
    """Build a CosmosClient using the connection string stored in Key Vault.
    Supports both connection string format (AccountEndpoint=...;AccountKey=...;)
    and plain key format.
    """
    from azure.cosmos import CosmosClient

    secret = _get_cosmos_secret_from_vault()
    if secret.startswith("AccountEndpoint="):
        return CosmosClient.from_connection_string(secret)
    return CosmosClient(config.cosmos_endpoint, secret)


def get_openai_token_provider():
    """Return an Entra ID token provider for Azure OpenAI (used when key auth is disabled)."""
    return get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
