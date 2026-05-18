"""Create the Cosmos DB NoSQL vector index for RetroDoc Bot.

Run once after Terraform provisioning, before the first ingestion:
  python -m data.create_index

Creates the 'vectors' container with the required vector embedding policy
and quantizedFlat index so AzureCosmosDBNoSqlVectorSearch can perform
ANN retrieval via the azure-cosmos SDK.

Prerequisites
-------------
  1. Azure Cosmos DB (NoSQL API) account provisioned (terraform apply)
  2. .env populated with COSMOS_ENDPOINT and COSMOS_KEY
"""
from azure.cosmos import CosmosClient, PartitionKey

from backend.agents.config import config

EMBEDDING_DIMENSIONS = 1536  # text-embedding-ada-002

VECTOR_EMBEDDING_POLICY = {
    "vectorEmbeddings": [
        {
            "path": "/embedding",
            "dataType": "float32",
            "distanceFunction": "cosine",
            "dimensions": EMBEDDING_DIMENSIONS,
        }
    ]
}

INDEXING_POLICY = {
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [{"path": "/embedding/*"}],
    "vectorIndexes": [{"path": "/embedding", "type": config.cosmos_vector_index_type}],
}


def create_vector_container() -> None:
    client = CosmosClient(config.cosmos_endpoint, config.cosmos_key)
    db = client.get_database_client(config.cosmos_database)

    db.create_container_if_not_exists(
        id=config.cosmos_vectors_container,
        partition_key=PartitionKey(path="/id"),
        vector_embedding_policy=VECTOR_EMBEDDING_POLICY,
        indexing_policy=INDEXING_POLICY,
    )
    print(
        f"Container '{config.cosmos_vectors_container}' ready in "
        f"database '{config.cosmos_database}'."
    )


if __name__ == "__main__":
    create_vector_container()
