"""RAG-based documentation generation approach.

Retrieves related code patterns and existing documentation from Cosmos DB
(NoSQL API) via AzureCosmosDBNoSqlVectorSearch before generating, giving
the model useful in-context examples.

Pipeline:  Cosmos DB vector retrieval → LLM prompt → Markdown documentation
"""
from azure.cosmos import CosmosClient, PartitionKey
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from backend.agents.config import config, get_cosmos_client, get_openai_token_provider

_SYSTEM_PROMPT = """\
You are a technical documentation expert. Generate clear, comprehensive Markdown \
documentation for the code supplied by the user.

Use the retrieved context below to mirror the project's existing documentation \
style, naming conventions, and patterns.

Retrieved context:
{context}

Include:
- **Overview** – what the code does and why it exists
- **Parameters / Arguments** – types, defaults, constraints
- **Return values / Outputs**
- **Usage examples**
- **Dependencies & side-effects**
- **Edge cases and limitations**
"""

DOC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", "Generate documentation for the following code:\n\n```\n{code}\n```"),
])


def _format_docs(docs) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def _build_chain():
    _openai_auth = (
        {"azure_ad_token_provider": get_openai_token_provider()}
        if not config.azure_openai_api_key
        else {"api_key": config.azure_openai_api_key}
    )
    llm = AzureChatOpenAI(
        azure_endpoint=config.azure_openai_endpoint,
        api_version=config.azure_openai_api_version,
        azure_deployment=config.azure_openai_deployment,
        **_openai_auth,
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=config.azure_openai_endpoint,
        azure_deployment=config.azure_openai_embedding_deployment,
        **_openai_auth,
    )
    cosmos_client = get_cosmos_client()
    container = (
        cosmos_client
        .get_database_client(config.cosmos_database)
        .get_container_client(config.cosmos_vectors_container)
    )
    vector_store = AzureCosmosDBNoSqlVectorSearch(
        embedding=embeddings,
        cosmos_client=cosmos_client,
        database_name=config.cosmos_database,
        container_name=config.cosmos_vectors_container,
        vector_embedding_policy={
            "vectorEmbeddings": [
                {
                    "path": "/embedding",
                    "dataType": "float32",
                    "distanceFunction": "cosine",
                    "dimensions": 1536,
                }
            ]
        },
        indexing_policy={
            "includedPaths": [{"path": "/*"}],
            "excludedPaths": [{"path": "/embedding/*"}],
            "vectorIndexes": [{"path": "/embedding", "type": config.cosmos_vector_index_type}],
        },
        cosmos_container_properties={"partition_key": PartitionKey(path="/id")},
        cosmos_database_properties={},
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    return (
        {"context": retriever | _format_docs, "code": RunnablePassthrough()}
        | DOC_PROMPT
        | llm
        | StrOutputParser()
    )


class RAGApproach:
    """Documentation generator using Retrieval-Augmented Generation."""

    def __init__(self):
        self._chain = _build_chain()

    def generate_documentation(self, code: str) -> str:
        """Generate Markdown documentation for *code* using retrieved context."""
        return self._chain.invoke(code)
