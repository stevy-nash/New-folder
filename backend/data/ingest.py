"""Ingest source code and documentation into Azure Blob Storage + Cosmos DB vector store.

Usage
-----
  # Ingest a single file
  python -m data.ingest path/to/doc.pdf

  # Ingest an entire directory (recursively)
  python -m data.ingest path/to/docs/

Prerequisites
-------------
  1. Azure resources provisioned (terraform apply)
  2. Vector container created (python -m data.create_index)
  3. .env populated with keys

Supported file types
--------------------
  .txt   → eTemptation   (pseudo-language)
  .docx  → Word          (Azure Document Intelligence prebuilt-layout)
  .pptx  → PowerPoint    (Azure Document Intelligence prebuilt-layout)
  .pdf   → PDF           (Azure Document Intelligence prebuilt-layout)
"""
import sys
from pathlib import Path

from azure.cosmos import PartitionKey
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.storage.blob import BlobServiceClient
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from backend.agents.config import config, get_cosmos_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CODE_EXTENSIONS = {".txt"}
DOC_EXTENSIONS = {".docx", ".pptx", ".pdf"}
SUPPORTED_EXTENSIONS = CODE_EXTENSIONS | DOC_EXTENSIONS

# ---------------------------------------------------------------------------
# eTemptation splitter  (.txt pseudo-language)
# ---------------------------------------------------------------------------

_ETEMPTATION_SEPARATORS = [
    # Rule boundaries
    r"\n\s*-\s*Règle\s*:\s*.+",
    r"\n\s*FIN\s*$",
    # Procedures
    r"\n\s*FINPROC\s*$",
    r"\n\s*PROC\s+[A-Z0-9_]+",
    # Dictionary & anomaly blocks
    r"\n\s*FINDICO\s*$",
    r"\n\s*DEBDICO\s*$",
    r"\n\s*FINANO\s*$",
    r"\n\s*DEBANO\s*$",
    # Iteration blocks
    r"\n\s*FINPOUR\s*$",
    r"\n\s*POUR\s+[A-Z0-9_]+",
    # Conditional blocks
    r"\n\s*FINSI\s*$",
    r"\n\s*SINON\s*$",
    r"\n\s*SI\s+.+",
    # Semantic instructions / DSL actions
    r"\n\s*DEF\s+LOCA_[A-Z0-9_]+",
    r"\n\s*ENLEVER\s+.+",
    r"\n\s*AJOUTER\s+.+",
    r"\n\s*ANOMALIE\s+\d+",
    r"\n\s*SUPANOM\s+\d+",
    r"\n\s*CALENDRIER\s+.+",
    r"\n\s*ANALYSE\s+.+",
    r"\n\s*PLAGE\s+\"?.+\"?",
    # Structural comments / headers
    r"\n\s*\\\*[-_]{5,}.*",
    r"\n\s*-\s+.+",
    # Fallbacks
    r"\n{2,}",
    r"\n",
]

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

_etemptation_splitter = RecursiveCharacterTextSplitter(
    separators=_ETEMPTATION_SEPARATORS,
    is_separator_regex=True,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)

# ---------------------------------------------------------------------------
# Markdown / Document Intelligence splitters
# ---------------------------------------------------------------------------

_MD_HEADERS = [
    ("#", "header_1"),
    ("##", "header_2"),
    ("###", "header_3"),
    ("####", "header_4"),
    ("#####", "header_5"),
    ("######", "header_6"),
]

_md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=_MD_HEADERS,
    strip_headers=False,
)
_fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
)


# ---------------------------------------------------------------------------
# Azure Document Intelligence helper
# ---------------------------------------------------------------------------

def _load_with_doc_intelligence(file_path: Path, base_metadata: dict) -> list[Document]:
    """Load a document via Azure Document Intelligence (markdown output) and chunk
    semantically using MarkdownHeaderTextSplitter, with a recursive fallback for
    oversized sections."""
    loader = AzureAIDocumentIntelligenceLoader(
        api_endpoint=config.azure_doc_intelligence_endpoint,
        api_key=config.azure_doc_intelligence_key,
        file_path=str(file_path),
        api_model="prebuilt-layout",
        mode="markdown",
    )
    raw_docs = loader.load()

    md_header_splits = []
    for raw_doc in raw_docs:
        md_header_splits.extend(_md_splitter.split_text(raw_doc.page_content))

    for chunk in md_header_splits:
        chunk.metadata.update(base_metadata)

    return _fallback_splitter.split_documents(md_header_splits)


# ---------------------------------------------------------------------------
# Blob upload helper
# ---------------------------------------------------------------------------

def _upload_blob(blob_service: BlobServiceClient, file_path: Path) -> None:
    container = blob_service.get_container_client(config.azure_storage_container)
    with open(file_path, "rb") as f:
        container.upload_blob(name=file_path.name, data=f, overwrite=True)
    print(f"    blob ← {file_path.name}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_file(
    file_path: Path,
    vector_store: AzureCosmosDBNoSqlVectorSearch,
) -> int:
    """Chunk, embed, and index *file_path* into *vector_store*.

    Returns the number of chunks indexed.
    Raises ``ValueError`` for unsupported file types.
    """
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    base_metadata = {"source_file": file_path.name}

    if ext in CODE_EXTENSIONS:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        base_metadata.update({"doc_type": "dsl", "language": "etemptation"})
        documents = [
            Document(page_content=c, metadata=base_metadata)
            for c in _etemptation_splitter.split_text(content)
        ]
    else:
        base_metadata["doc_type"] = "documentation"
        if ext in (".docx", ".pptx", ".pdf"):
            documents = _load_with_doc_intelligence(file_path, base_metadata)
        elif ext == ".md":
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            md_splits = _md_splitter.split_text(content)
            for chunk in md_splits:
                chunk.metadata.update(base_metadata)
            documents = _fallback_splitter.split_documents(md_splits)

    vector_store.add_documents(documents)
    print(f"    indexed {len(documents)} chunk(s) from {file_path.name}")
    return len(documents)


def build_vector_store() -> AzureCosmosDBNoSqlVectorSearch:
    """Construct and return the Cosmos DB vector store with embeddings wired up."""
    _openai_auth = (
        {"azure_ad_token_provider": get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )}
        if not config.azure_openai_api_key
        else {"api_key": config.azure_openai_api_key}
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=config.azure_openai_endpoint,
        azure_deployment=config.azure_openai_embedding_deployment,
        **_openai_auth,
    )
    cosmos_client = get_cosmos_client()
    return AzureCosmosDBNoSqlVectorSearch(
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


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m data.ingest <file_or_directory>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"[error] Path not found: {target}")
        sys.exit(1)

    vector_store = build_vector_store()
    blob_service = BlobServiceClient(
        account_url=f"https://{config.azure_storage_account}.blob.core.windows.net",
        credential=config.azure_storage_key,
    )

    files = [target] if target.is_file() else [f for f in target.rglob("*") if f.is_file()]
    print(f"Processing {len(files)} file(s) from '{target}' ...\n")

    for file_path in files:
        print(f"  {file_path.relative_to(target.parent if target.is_file() else target)}")
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"    skip  (unsupported type: {ext})")
            continue
        _upload_blob(blob_service, file_path)
        process_file(file_path, vector_store)

    print("\nIngestion complete.")


if __name__ == "__main__":
    main()
