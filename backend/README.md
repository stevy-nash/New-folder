# RetroDoc Bot MVP

AI agent that generates documentation from source code and existing docs.  
Benchmarks two strategies — **RAG** (retrieval-augmented) vs **Prompt-Based** — so you can measure quality vs cost trade-offs with GPT-5 on Azure AI Foundry.

---

## Architecture

```
                         HTTP clients
                              │
              ┌───────────────┼───────────────┐
              │               │               │
   POST /api/ingest    POST /api/generate   CLI (agents/main.py)
              │               │               │
   ┌──────────▼───────────────▼──────────┐    │
   │          app/ (Azure Functions)     │    │
   │                                     │    │
   │  ingest_document_http()             │    │
   │    → data.ingest.process_file()     │    │
   │                                     │    │
   │  generate_documentation_http()      │    │
   │    → RAGApproach / PromptBased ─────┼────┘
   └──────────┬──────────────────────────┘
              │                │
   ┌──────────▼───┐   ┌────────▼────────────────────┐
   │ Blob Storage │   │ agents/rag/ + prompt_based/  │
   │ (raw files)  │   │    ↓ retrieve  ↓ generate    │
   └──────────────┘   │  Cosmos DB   Azure AI Foundry│
                      │  vector store  (GPT-5)       │
                      │  (diskANN)                   │
                      └──────────────────────────────┘
                              │
                      ┌───────▼───────┐
                      │ Cosmos DB     │
                      │ (sessions)    │
                      └───────────────┘
```

## Azure Resources

| Resource | Terraform name | Azure name |
|---|---|---|
| Resource Group | `azurerm_resource_group.rg` | `horoquartz-subs-ia-re-rg` |
| Blob Storage | `azurerm_storage_account.storage` | `subsiarecs`* |
| Cosmos DB | `azurerm_cosmosdb_account.cosmos` | `subs-ia-re-cosmos` |
| AI Foundry | `azurerm_cognitive_account.foundry` | `subs-ia-re-iafoundry` |
| Document Intelligence | (existing) | `subs-ia-re-docintel` |

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) — logged in (`az login`)
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) v4 (for local Function App dev)
- Python ≥ 3.11

---

## Quick Start

### Install Python dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 3 — Create the vector index

```bash
python -m data.create_index
```

### 4 — Ingest your codebase (CLI or HTTP)

```bash
# Ingest a directory
python -m data.ingest path/to/your/src/

# Or a single file
python -m data.ingest path/to/module.py
```

### 5 — Run / deploy the Function App

The Function App exposes two HTTP endpoints (see [API Reference](#function-app-api-reference) below).

Run locally:

```bash
cd app
func start
```

Deploy to Azure:

```bash
cd app
func azure functionapp publish <AZURE_FUNCTION_APP_NAME>
```

Fill in `AZURE_FUNCTION_APP_NAME` in your `.env` before deploying.

### 6 — Generate documentation

```bash
# RAG approach (uses retrieved context)
python -m agents.main path/to/module.py --approach rag

# Prompt-based approach (direct prompt, no retrieval)
python -m agents.main path/to/module.py --approach prompt

# Benchmark both approaches and compare
python -m agents.main path/to/module.py --approach benchmark
```

---

## Benchmark output

`--approach benchmark` runs both chains on the same input, prints a summary table, and writes:

- `<file>_doc_rag.md`
- `<file>_doc_prompt_based.md`

Results (latency, output length, timestamps) are persisted to the `benchmark_results` Cosmos DB container so you can query trends over time.

---

## Project structure

```
.
├── agents/                       # Documentation generation agents
│   ├── config.py                 # Reads .env into a Config dataclass
│   ├── main.py                   # CLI entry point
│   ├── rag/
│   │   └── rag.py                # RAG chain (Cosmos DB vector store → GPT-5)
│   ├── prompt_based/
│   │   └── prompt_based.py       # Direct prompt chain (GPT-5)
│   └── memory/
│       └── cosmos_history.py     # Cosmos DB session persistence
│
├── data/                         # Vector store, ingestion, and data utilities
│   ├── create_index.py           # One-time Cosmos DB vector container setup
│   └── ingest.py                 # Chunk, embed, and index source files
│                                 # Public API: process_file(), build_vector_store()
│
├── app/                          # Azure Function App (HTTP-triggered ingestion & inference)
│   ├── function_app.py           # POST /api/ingest  — ingest a document
│   │                             # POST /api/generate — generate documentation
│   ├── host.json                 # Functions host config (v2, extension bundle v4)
│   ├── requirements.txt          # Function App Python dependencies
│   └── local.settings.json       # Local dev settings (gitignored — fill from .env)
│
├── eval/
│   └── runner.py                 # Side-by-side benchmark + Cosmos persistence
│
├── requirements.txt              # Project-wide Python dependencies
├── .env.example
└── .gitignore
```

---

## Supported file types

| Extension | Pipeline |
|-----------|---------|
| `.txt` | eTemptation DSL splitter (custom regex separators) |
| `.pdf` | Azure Document Intelligence → Markdown header splitter |
| `.docx` | Azure Document Intelligence → Markdown header splitter |
| `.pptx` | Azure Document Intelligence → Markdown header splitter |

---

## Function App API Reference

### `POST /api/ingest`

Chunks, embeds, and indexes a document into the Cosmos DB vector store.

| | |
|---|---|
| **Content-Type** | `multipart/form-data` |
| **Field** | `file` — any supported document (`.txt`, `.pdf`, `.docx`, `.pptx`) |
| **Auth** | `x-functions-key` header or `?code=` query param |

**Response:**
```json
{ "filename": "paie_calcul.pdf", "chunks": 42 }
```

```bash
curl -X POST "http://localhost:7071/api/ingest" \
     -F "file=@paie_calcul.pdf"
```

---

### `POST /api/generate`

Generates Markdown documentation from a `.txt` source code file.

| | |
|---|---|
| **Content-Type** | `multipart/form-data` |
| **Field** | `file` — `.txt` source code file |
| **Query param** | `approach=rag` (default) \| `approach=prompt` |
| **Auth** | `x-functions-key` header or `?code=` query param |

**Response:**
```json
{
  "filename": "module.txt",
  "approach": "rag",
  "session_id": "3f2a...",
  "documentation": "# Module\n\n..."
}
```

```bash
# RAG approach (default)
curl -X POST "http://localhost:7071/api/generate" \
     -F "file=@module.txt"

# Prompt-based approach
curl -X POST "http://localhost:7071/api/generate?approach=prompt" \
     -F "file=@module.txt"
```

---

## Approach comparison

| | RAG | Prompt-Based |
|---|---|---|
| **Retrieval** | Cosmos DB vector store (diskANN) | None |
| **Context** | Similar code/docs from your codebase | None |
| **Consistency** | Mirrors project conventions | Model defaults |
| **Latency** | Higher (retrieval + generation) | Lower |
| **Token cost** | Higher (context + generation) | Lower |
| **Best for** | Large codebases with existing docs | Quick, one-off generation |
