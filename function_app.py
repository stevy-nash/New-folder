"""Azure Function — Document Ingestion & Inference (HTTP Triggers)

Routes:
  POST /api/ingest   — multipart/form-data 'file' field → chunk, embed, index
  POST /api/generate — multipart/form-data 'file' (.txt) + optional 'approach'
                       query param (rag | prompt, default: rag) → Markdown doc

Both delegate to the agents/ and data/ packages.
"""
import base64
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

from langchain_community.vectorstores.azure_cosmos_db_no_sql import (
    AzureCosmosDBNoSqlVectorSearch,
)

from backend.agents.memory.cosmos_history import CosmosSessionHistory
from backend.agents.prompt_based.prompt_based import PromptBasedApproach
from backend.agents.rag.rag import RAGApproach
from backend.data.ingest import SUPPORTED_EXTENSIONS, build_vector_store, process_file

# ---------------------------------------------------------------------------
# Lazy-initialised vector store  (reused across warm invocations)
# ---------------------------------------------------------------------------

_vector_store: AzureCosmosDBNoSqlVectorSearch | None = None


def _get_vector_store() -> AzureCosmosDBNoSqlVectorSearch:
    global _vector_store
    if _vector_store is None:
        _vector_store = build_vector_store()
    return _vector_store


# ---------------------------------------------------------------------------
# Storage helpers — async job queue and blob I/O
# ---------------------------------------------------------------------------

_JOBS_QUEUE        = os.getenv("AZURE_STORAGE_QUEUE")
_INPUTS_CONTAINER  = os.getenv("AZURE_STORAGE_INPUTS_CONTAINER")
_OUTPUTS_CONTAINER = os.getenv("AZURE_STORAGE_OUTPUTS_CONTAINER")
_TABLES_CONTAINER  = os.getenv("AZURE_STORAGE_CLIENT_CONTAINER")


def _storage_account_name() -> str:
    return os.environ.get("AzureWebJobsStorage__accountName")


def _blob_service() -> BlobServiceClient:
    name = _storage_account_name()
    return BlobServiceClient(f"https://{name}.blob.core.windows.net", credential=DefaultAzureCredential())


def _queue_service() -> QueueServiceClient:
    name = _storage_account_name()
    return QueueServiceClient(f"https://{name}.queue.core.windows.net", credential=DefaultAzureCredential())


def _ensure_container_exists(blob_svc: BlobServiceClient, name: str) -> None:
    try:
        blob_svc.create_container(name)
    except Exception:
        pass  # already exists


def _ensure_queue_exists(queue_svc: QueueServiceClient, name: str) -> None:
    try:
        queue_svc.create_queue(name)
    except Exception:
        pass  # already exists


# ---------------------------------------------------------------------------
# Azure Function app
# ---------------------------------------------------------------------------

app = func.FunctionApp()


# ---------------------------------------------------------------------------
# Shared helper — write bytes to a named temp file and ingest
# ---------------------------------------------------------------------------

def _ingest_bytes(filename: str, data: bytes) -> int:
    """Write *data* to a temp file named *filename*, run the ingestion pipeline,
    clean up, and return the number of chunks indexed."""
    tmp_dir = Path(tempfile.mkdtemp())
    named_path = tmp_dir / filename
    try:
        named_path.write_bytes(data)
        return process_file(named_path, _get_vector_store())
    finally:
        named_path.unlink(missing_ok=True)
        tmp_dir.rmdir()


# ---------------------------------------------------------------------------
# Azure Function — HTTP Trigger
# ---------------------------------------------------------------------------

@app.route(route="ingest", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def ingest_document_http(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/ingest

    Accepts multipart/form-data with one or more 'file' fields.
    Returns JSON: {"results": [{"filename": "...", "chunks": N}, ...]}

    Example (curl):
      curl -X POST "http://localhost:7071/api/ingest?code=<key>" \\
           -F "file=@paie_calcul.pdf" \\
           -F "file=@module.txt"
    """
    files = req.files.getlist("file")
    if not files:
        return func.HttpResponse(
            json.dumps({"error": "No 'file' field found in the request. Send multipart/form-data with one or more 'file' fields."}),
            status_code=400,
            mimetype="application/json",
        )

    results = []
    has_error = False

    for file_data in files:
        filename = Path(file_data.filename).name  # strip any path from the client
        ext = Path(filename).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            results.append({
                "filename": filename,
                "error": f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
            })
            has_error = True
            continue

        logging.info("HTTP ingest request for: %s", filename)
        data = file_data.read()

        try:
            n = _ingest_bytes(filename, data)
            results.append({"filename": filename, "chunks": n})
        except Exception as exc:
            logging.exception("Ingestion failed for '%s'", filename)
            results.append({"filename": filename, "error": str(exc)})
            has_error = True

    status_code = 207 if has_error and len(results) > 1 else (500 if has_error else 200)
    return func.HttpResponse(
        json.dumps({"results": results}),
        status_code=status_code,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# Azure Function — HTTP Trigger: generate (async, returns 202)
# ---------------------------------------------------------------------------

@app.route(route="generate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def generate_documentation_http(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/generate

    Uploads .txt file(s) to blob storage, enqueues a generation job, and
    returns 202 Accepted immediately with a job_id.
    Poll GET /api/status/{job_id} for the result.

    Optional query params:
      approach=rag      — RAG chain
      approach=prompt   (default) — direct prompt
      version=v15       — client-specific tables

    Returns 202: {"job_id": "...", "files": [...], "status_url": "/api/status/{job_id}"}
    """
    files = req.files.getlist("file")
    if not files:
        return func.HttpResponse(
            json.dumps({"error": "No 'file' field found in the request."}),
            status_code=400,
            mimetype="application/json",
        )

    approach_name = req.params.get("approach", "prompt").lower()
    if approach_name not in ("rag", "prompt"):
        return func.HttpResponse(
            json.dumps({"error": "Invalid 'approach' param. Use 'rag' or 'prompt'."}),
            status_code=400,
            mimetype="application/json",
        )

    version = req.params.get("version", None)
    _SUPPORTED_VERSIONS = {"v15"}
    if version is not None and version.lower() not in _SUPPORTED_VERSIONS:
        return func.HttpResponse(
            json.dumps({"error": f"Unsupported 'version' param '{version}'."}),
            status_code=400,
            mimetype="application/json",
        )

    job_id = str(uuid.uuid4())
    blob_svc = _blob_service()
    queue_svc = _queue_service()
    _ensure_container_exists(blob_svc, _INPUTS_CONTAINER)
    _ensure_queue_exists(queue_svc, _JOBS_QUEUE)

    uploaded: list[str] = []
    skipped: list[dict] = []

    for file_data in files:
        filename = Path(file_data.filename).name
        if Path(filename).suffix.lower() != ".txt":
            skipped.append({"filename": filename, "error": "Only .txt files are accepted."})
            continue
        code_bytes = file_data.read()
        blob_svc.get_blob_client(_INPUTS_CONTAINER, f"{job_id}/{filename}").upload_blob(
            code_bytes, overwrite=True
        )
        uploaded.append(filename)
        logging.info("Input blob uploaded: %s/%s/%s", _INPUTS_CONTAINER, job_id, filename)

    if not uploaded:
        return func.HttpResponse(
            json.dumps({"error": "No valid .txt files provided.", "details": skipped}),
            status_code=400,
            mimetype="application/json",
        )

    msg_payload = json.dumps({"job_id": job_id, "files": uploaded, "approach": approach_name, "version": version})
    queue_svc.get_queue_client(_JOBS_QUEUE).send_message(
        base64.b64encode(msg_payload.encode()).decode()
    )
    logging.info("Job enqueued: job_id=%s files=%s approach=%s", job_id, uploaded, approach_name)

    body: dict = {"job_id": job_id, "files": uploaded, "status_url": f"/api/status/{job_id}"}
    if skipped:
        body["skipped"] = skipped
    return func.HttpResponse(json.dumps(body), status_code=202, mimetype="application/json")


# ---------------------------------------------------------------------------
# Azure Function — Blob Trigger: ZIP upload → full-batch generation job
# ---------------------------------------------------------------------------

@app.blob_trigger(
    arg_name="blob",
    path=f"{_TABLES_CONTAINER}/{{name}}",
    connection="AzureWebJobsStorage",
)
def process_client_reglementaire(blob: func.InputStream) -> None:
    """Triggered when a .zip is uploaded to the retrodoc-tables container.

    The ZIP must contain hopprog.csv and hopregl.csv (semicolon-separated).
    All rules found in hopregl.csv are extracted via prepare_inference logic,
    uploaded to retrodoc-inputs, and a single generation job is enqueued.
    """
    import io
    import zipfile
    import tempfile as _tempfile
    import shutil

    if not blob.name.lower().endswith(".zip"):
        logging.info("Skipping non-zip blob: %s", blob.name)
        return

    logging.info("ZIP upload detected: %s (%d bytes)", blob.name, blob.length)

    zip_bytes = blob.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        logging.error("Bad ZIP file: %s", blob.name)
        return

    # Locate hopprog.csv and hopregl.csv inside the ZIP (any subfolder)
    names_in_zip = zf.namelist()
    def _find(stem: str) -> str | None:
        for n in names_in_zip:
            if stem.lower() in Path(n).name.lower():
                return n
        return None

    hopprog_entry = _find("hopprog.")
    hopregl_entry = _find("hopregl.")

    if not hopprog_entry or not hopregl_entry:
        logging.error(
            "ZIP %s missing hopprog.* or hopregl.* (found: %s)",
            blob.name, names_in_zip,
        )
        return

    # All lookup table stems we want to extract from the ZIP (normalized blob name → search stem)
    _LOOKUP_STEMS = {
        "hopprog.csv":        "hopprog.",
        "hopregl.csv":        "hopregl.",
        "hopdico.csv":        "hopdico.",
        "hopcode.csv":        "hopcode.",
        "hopmess.csv":        "hopmess.",
        "hopmoti.csv":        "hopmoti.",
        "affichage_ecran.csv": "affichage_ecran",
    }

    tmp_dir = Path(_tempfile.mkdtemp())
    try:
        hopprog_path = tmp_dir / "hopprog.csv"
        hopregl_path = tmp_dir / "hopregl.csv"
        hopprog_path.write_bytes(zf.read(hopprog_entry))
        hopregl_path.write_bytes(zf.read(hopregl_entry))

        # Import prepare_inference helpers
        from backend.utils.prepare_inference import _all_rule_names, extract_rule

        rule_names = _all_rule_names(str(hopprog_path))
        logging.info("Found %d rules to generate", len(rule_names))

        job_id = str(uuid.uuid4())
        blob_svc = _blob_service()
        queue_svc = _queue_service()
        _ensure_container_exists(blob_svc, _INPUTS_CONTAINER)
        _ensure_queue_exists(queue_svc, _JOBS_QUEUE)

        # Upload all available lookup tables to {job_id}/_tables/ in retrodoc-inputs
        for blob_name, stem in _LOOKUP_STEMS.items():
            entry = _find(stem)
            if entry:
                blob_svc.get_blob_client(_INPUTS_CONTAINER, f"{job_id}/_tables/{blob_name}").upload_blob(
                    zf.read(entry), overwrite=True
                )
                logging.info("Uploaded lookup table: %s/_tables/%s", job_id, blob_name)
            else:
                logging.warning("Lookup table not found in ZIP: %s", stem)

        uploaded: list[str] = []
        for rule_name in rule_names:
            try:
                lines = extract_rule(rule_name, str(hopprog_path), strip_comments=False)
                txt_name = f"{rule_name}.txt"
                txt_bytes = "\n".join(lines).encode("utf-8")
                blob_svc.get_blob_client(_INPUTS_CONTAINER, f"{job_id}/{txt_name}").upload_blob(
                    txt_bytes, overwrite=True
                )
                uploaded.append(txt_name)
            except Exception:
                logging.exception("Failed to extract rule '%s'", rule_name)

        if not uploaded:
            logging.error("No rules extracted from ZIP %s", blob.name)
            return

        msg_payload = json.dumps({
            "job_id": job_id,
            "files": uploaded,
            "approach": "prompt",
            "version": None,
            "client_tables": True,
        })
        queue_svc.get_queue_client(_JOBS_QUEUE).send_message(
            base64.b64encode(msg_payload.encode()).decode()
        )
        logging.info(
            "Batch job enqueued: job_id=%s rules=%d source_zip=%s",
            job_id, len(uploaded), blob.name,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Azure Function — Queue Trigger: process generation job
# ---------------------------------------------------------------------------

@app.queue_trigger(arg_name="msg", queue_name="retrodoc-jobs", connection="AzureWebJobsStorage")
def process_generate_job(msg: func.QueueMessage) -> None:
    """Dequeues a generation job, runs the LLM pipeline, and saves the output
    to the blob container  retrodoc-outputs/{job_id}/doc_{stem}.md.
    """
    raw = msg.get_body()
    try:
        payload = json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        payload = json.loads(raw.decode("utf-8"))

    job_id: str = payload["job_id"]
    filenames: list[str] = payload["files"]
    approach_name: str = payload.get("approach", "prompt")
    version: str | None = payload.get("version")
    client_tables: bool = payload.get("client_tables", False)

    logging.info("Processing job: job_id=%s files=%s approach=%s client_tables=%s", job_id, filenames, approach_name, client_tables)

    blob_svc = _blob_service()
    _ensure_container_exists(blob_svc, _OUTPUTS_CONTAINER)

    # If the job was submitted with client-provided lookup tables, download them
    # and build a TablePaths pointing at the local temp copies.
    client_table_paths = None
    _tables_tmp_dir = None
    if client_tables and approach_name != "rag":
        try:
            import tempfile as _tempfile2
            from backend.agents.prompt_based.get_lookup import TablePaths
            _tables_tmp_dir = Path(_tempfile2.mkdtemp())
            for tblob in blob_svc.get_container_client(_INPUTS_CONTAINER).list_blobs(
                name_starts_with=f"{job_id}/_tables/"
            ):
                local_name = Path(tblob.name).name
                (_tables_tmp_dir / local_name).write_bytes(
                    blob_svc.get_blob_client(_INPUTS_CONTAINER, tblob.name)
                             .download_blob().readall()
                )
            d = _tables_tmp_dir
            def _tp(name: str) -> str:
                return str(d / name)
            _std_hopprog = Path(__file__).parent / "backend" / "assets" / "v15" / "Sources standard" / "hopprog.bdd"
            client_table_paths = TablePaths(
                ecran_csv=_tp("affichage_ecran.csv"),
                hopdico_csv=_tp("hopdico.csv"),
                hopcode_csv=_tp("hopcode.csv"),
                hopmess_csv=_tp("hopmess.csv"),
                hopmoti_csv=_tp("hopmoti.csv"),
                hopregl_csv=_tp("hopregl.csv"),
                standard_hopprog_path=str(_std_hopprog) if _std_hopprog.is_file() else None,
            )
            logging.info("Client TablePaths built from %d blobs in %s/_tables/", sum(1 for _ in d.iterdir()), job_id)
        except Exception:
            logging.exception("Failed to build client TablePaths for job=%s — falling back to defaults", job_id)
            client_table_paths = None

    approach = RAGApproach() if approach_name == "rag" else PromptBasedApproach(version=version, table_paths=client_table_paths)

    for filename in filenames:
        input_blob = blob_svc.get_blob_client(_INPUTS_CONTAINER, f"{job_id}/{filename}")
        try:
            code = input_blob.download_blob().readall().decode("utf-8", errors="ignore")
        except Exception:
            logging.exception("Failed to download input blob: job=%s file=%s", job_id, filename)
            continue

        try:
            documentation = approach.generate_documentation(code)
        except Exception as exc:
            logging.exception("Generation failed: job=%s file=%s", job_id, filename)
            blob_svc.get_blob_client(_OUTPUTS_CONTAINER, f"{job_id}/error_{Path(filename).stem}.txt").upload_blob(
                str(exc).encode("utf-8"), overwrite=True
            )
            continue

        output_blob_name = f"{job_id}/tmp/doc_{Path(filename).stem}.md"
        blob_svc.get_blob_client(_OUTPUTS_CONTAINER, output_blob_name).upload_blob(
            documentation.encode("utf-8"), overwrite=True
        )
        logging.info("Output blob saved: %s/%s", _OUTPUTS_CONTAINER, output_blob_name)

        try:
            input_blob.delete_blob()
        except Exception:
            pass

        try:
            history = CosmosSessionHistory()
            history.save(approach=approach_name, code=code, documentation=documentation)
            logging.info("Session saved: %s", history.session_id)
        except Exception:
            logging.warning("Failed to save history: job=%s file=%s", job_id, filename)

    # -----------------------------------------------------------------------
    # Post-loop: merge all generated .md blobs into a single combined.docx
    # -----------------------------------------------------------------------
    try:
        import shutil
        import subprocess
        import tempfile as _tempfile

        md_blobs = sorted(
            [b for b in blob_svc.get_container_client(_OUTPUTS_CONTAINER)
                                 .list_blobs(name_starts_with=f"{job_id}/tmp/doc_")
             if b.name.endswith(".md")],
            key=lambda b: b.name,
        )

        if md_blobs:
            tmp_dir = Path(_tempfile.mkdtemp())
            try:
                page_break = (
                    "\n\n```{=openxml}\n"
                    "<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n"
                    "```\n\n"
                )
                parts = []
                for blob_item in md_blobs:
                    content = (
                        blob_svc.get_blob_client(_OUTPUTS_CONTAINER, blob_item.name)
                                 .download_blob().readall().decode("utf-8", errors="ignore")
                    )
                    parts.append(content)

                merged_path = tmp_dir / "merged.md"
                merged_path.write_text(page_break.join(parts), encoding="utf-8")

                lua_filter = Path(__file__).parent / "scripts" / "full-width-tables.lua"
                docx_path = tmp_dir / "documentation.docx"

                _bundled_pandoc = Path(__file__).parent / "pandoc"
                _pandoc_bin = str(_bundled_pandoc) if _bundled_pandoc.exists() else "pandoc"
                cmd = [
                    _pandoc_bin, str(merged_path),
                    "--from", "markdown",
                    "--to", "docx",
                    "--output", str(docx_path),
                    "--standalone",
                ]
                if lua_filter.exists():
                    cmd += ["--lua-filter", str(lua_filter)]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    docx_blob_name = f"{job_id}/documentation.docx"
                    blob_svc.get_blob_client(_OUTPUTS_CONTAINER, docx_blob_name).upload_blob(
                        docx_path.read_bytes(), overwrite=True
                    )
                    logging.info("docx saved: %s/%s", _OUTPUTS_CONTAINER, docx_blob_name)

                    # Delete the tmp .md blobs now that docx is ready
                    for blob_item in md_blobs:
                        try:
                            blob_svc.get_blob_client(_OUTPUTS_CONTAINER, blob_item.name).delete_blob()
                        except Exception:
                            logging.warning("Could not delete tmp blob: %s", blob_item.name)
                    logging.info("Deleted %d tmp md blobs for job=%s", len(md_blobs), job_id)
                else:
                    logging.warning("pandoc failed for job=%s: %s", job_id, result.stderr)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        logging.exception("Failed to generate docx for job=%s", job_id)
    finally:
        if _tables_tmp_dir is not None:
            import shutil as _shutil
            _shutil.rmtree(_tables_tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Azure Function — HTTP Trigger: job status
# ---------------------------------------------------------------------------

@app.route(route="status/{job_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/status/{job_id}

    Returns 202 while the job is still processing, or 200 with the results
    once all output blobs are available.
    """
    job_id = req.route_params.get("job_id", "")
    if not job_id:
        return func.HttpResponse(
            json.dumps({"error": "Missing job_id."}), status_code=400, mimetype="application/json"
        )

    blob_svc = _blob_service()

    # Count total input files to compute progress
    try:
        total_inputs = sum(
            1 for _ in blob_svc.get_container_client(_INPUTS_CONTAINER)
                                .list_blobs(name_starts_with=f"{job_id}/")
        )
    except Exception:
        total_inputs = 0

    # Count generated output blobs (tmp .md files still in progress, or final docx)
    try:
        output_blobs = list(
            blob_svc.get_container_client(_OUTPUTS_CONTAINER)
                    .list_blobs(name_starts_with=f"{job_id}/")
        )
    except Exception:
        output_blobs = []

    # Final docx present → job is done
    final_blobs = [b for b in output_blobs if not b.name.startswith(f"{job_id}/tmp/")]
    completed = len([b for b in output_blobs if b.name.startswith(f"{job_id}/tmp/doc_") and b.name.endswith(".md")])

    # total = already generated (outputs) + still pending (inputs)
    total = completed + total_inputs
    progress_pct = round(completed / total * 100) if total > 0 else 0

    is_done = any(b.name.endswith(".docx") for b in final_blobs)

    if not output_blobs and total_inputs == 0:
        return func.HttpResponse(
            json.dumps({"job_id": job_id, "status": "not_found"}),
            status_code=404,
            mimetype="application/json",
        )

    if not is_done:
        return func.HttpResponse(
            json.dumps({
                "job_id": job_id,
                "status": "processing",
                "progress": progress_pct,
            }),
            status_code=202,
            mimetype="application/json",
        )

    results = []
    has_error = False
    for blob_item in final_blobs:
        stem = Path(blob_item.name).name
        if stem.startswith("error_"):
            content = (
                blob_svc.get_blob_client(_OUTPUTS_CONTAINER, blob_item.name)
                         .download_blob().readall().decode("utf-8", errors="ignore")
            )
            results.append({"filename": stem, "error": content})
            has_error = True
        else:
            results.append({"filename": stem})

    return func.HttpResponse(
        json.dumps({
            "job_id": job_id,
            "status": "done",
            "progress": 100,
            "results": results,
        }),
        status_code=207 if has_error else 200,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# Azure Function — HTTP Trigger: evaluation
# ---------------------------------------------------------------------------

@app.route(route="evaluate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def evaluate_documentation_http(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/evaluate

    Evaluates generated documentation quality using LLM-as-a-judge (DeepEval GEval).

    Accepts multipart/form-data with:
      - 'rule' (text field): DSL rule name, e.g. 'IACQCP'
      - 'doc'  (file field): generated .md documentation file

    Returns JSON: the EvalResult dataclass serialised as a flat object.

    Example (curl):
      curl -X POST "http://localhost:7071/api/evaluate?code=<key>" \\
           -F "rule=IACQCP" -F "doc=@outputs/doc_IACQCP_sans_commentaire.md"
    """
    import shutil

    from backend.eval.llm_eval import LLMEvaluator, EvalResult, save_csv

    _INPUTS_DIR = Path(__file__).parent / "inputs"

    rule_name = req.form.get("rule")
    doc_file = req.files.get("doc")

    if not rule_name or not doc_file:
        return func.HttpResponse(
            json.dumps({"error": "Both 'rule' (form field) and 'doc' (file upload) are required."}),
            status_code=400,
            mimetype="application/json",
        )

    tmp_dir = Path(tempfile.mkdtemp())
    tmp_outputs = tmp_dir / "outputs"
    tmp_outputs.mkdir()
    try:
        (tmp_outputs / f"doc_{rule_name}_sans_commentaire.md").write_bytes(doc_file.read())
        logging.info("HTTP evaluate: rule=%s", rule_name)
        result = LLMEvaluator().evaluate_one(rule_name, _INPUTS_DIR, tmp_outputs)
    except Exception as exc:
        logging.exception("Evaluation failed for rule '%s'", rule_name)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}), status_code=500, mimetype="application/json"
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    eval_dir = Path(__file__).parent / "outputs" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    csv_path = eval_dir / f"eval_{rule_name}.csv"
    save_csv([result], csv_path)
    logging.info("Eval results saved: %s", csv_path)
    csv_content = csv_path.read_text(encoding="utf-8")

    return func.HttpResponse(
        csv_content,
        status_code=200,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="eval_{rule_name}.csv"'},
    )
