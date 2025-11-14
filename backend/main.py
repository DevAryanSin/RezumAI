from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import Optional, List, Any
from uuid import uuid4
import json
import shutil
from pathlib import Path
import datetime
from fastapi import UploadFile, File, Form

# Optional PDF parser and Google auth libraries. We import inside try/except so
# the app still runs even if these are not installed; create_embeddings_for_pdf
# will fall back to a stub when libraries are missing.
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import aiplatform
except Exception:
    service_account = None
    AuthorizedSession = None
    aiplatform = None

app = FastAPI(title="RezumAI-backend", version="0.1")

# CORS - allow frontend dev; adjust in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn")

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    source: str


def call_vertex_ai(prompt: str) -> str:
    """Attempt to call Vertex AI (if library available). Falls back to a mock reply.

    Replace environment variables and adjust model usage to your setup.
    """
    project = os.environ.get("VERTEX_PROJECT")
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    model = os.environ.get("VERTEX_MODEL_ID")  # e.g. "text-bison@001" or your model resource

    try:
        from google.cloud import aiplatform
        # NOTE: This example uses the low-level PredictionServiceClient via aiplatform.gapic
        client = aiplatform.gapic.PredictionServiceClient()
        name = f"projects/{project}/locations/{location}/publishers/google/models/{model}"

        instance = {"content": prompt}
        request = {
            "endpoint": name,
            "instances": [instance],
            # "parameters": {...},
        }
        # The exact request/response shape depends on model and SDK versions.
        response = client.predict(request=request)
        # Try to extract a sensible text reply from response
        if response.predictions:
            # This will depend on the model. We conservatively join text fields.
            parts = []
            for p in response.predictions:
                if isinstance(p, dict):
                    # look for 'content' or 'text'
                    for k in ("content", "text", "output"):
                        if k in p:
                            parts.append(str(p[k]))
                else:
                    parts.append(str(p))
            return "\n".join(parts) if parts else str(response)
        return str(response)
    except Exception as e:
        # If Vertex SDK or credentials are not available, return a helpful mock reply
        logger.warning("Vertex AI call failed or not configured: %s", e)
        return (
            "[vertex-mock] I would call Vertex AI here if configured.\n"
            "Set VERTEX_PROJECT, VERTEX_LOCATION, and VERTEX_MODEL_ID environment variables and install google-cloud-aiplatform."
        )


def generate_agora_token(uid: Optional[str] = None) -> str:
    """Placeholder for generating an Agora token.

    Replace with Agora's official token builder/server-side SDK to create RTC/RTM tokens.
    Example env vars: AGORA_APP_ID, AGORA_APP_CERTIFICATE
    """
    app_id = os.environ.get("AGORA_APP_ID")
    app_cert = os.environ.get("AGORA_APP_CERTIFICATE")
    if not app_id or not app_cert:
        logger.warning("Agora credentials not set; returning mock token")
        return "MOCK_AGORA_TOKEN"

    # TODO: Use Agora's official token builder from their Python SDK.
    # For now return a placeholder string to show where to plug in token logic.
    return f"AGORA_TOKEN_FOR_{uid or 'anon'}"


# --- Upload / Batch helpers and endpoint -------------------------------------------------

# Configuration
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024))  # 10 MB default
MAX_FILES_PER_BATCH = int(os.environ.get("MAX_FILES_PER_BATCH", 100))
UPLOAD_BASE = Path(os.environ.get("UPLOAD_BASE", "./uploads"))


def save_file_to_storage(upload_file: UploadFile, dest_path: Path) -> Path:
    """Save an UploadFile to disk at dest_path. Returns the saved file path.

    In production this can be replaced to upload to GCS instead of local disk.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("wb") as f:
        # stream copy
        shutil.copyfileobj(upload_file.file, f)
    return dest_path


def create_embeddings_for_pdf(file_path: str, batch_id: str) -> str:
    """Extract text from the PDF and create embeddings via Vertex AI when possible.

    Behavior:
    - If `pypdf` and `google-cloud-aiplatform` are available and VERTEX_PROJECT + model
      are configured, attempt to call Vertex Embeddings and persist embeddings JSON.
    - Otherwise, fall back to a lightweight stub that logs a job id.

    The service account credentials can be provided in two ways:
    - Set env var `VERTEX_SERVICE_ACCOUNT_JSON` to the raw JSON string of the service account.
    - Or set `GOOGLE_APPLICATION_CREDENTIALS` to a path to a service account JSON file (ADC).
    """
    job_id = f"job-{uuid4()}"

    # 1) Extract text from PDF (best-effort)
    text = ""
    try:
        if PdfReader is None:
            raise RuntimeError("PDF parser (pypdf) not installed")
        reader = PdfReader(file_path)
        pages = []
        for p in reader.pages:
            try:
                t = p.extract_text()
            except Exception:
                t = None
            if t:
                pages.append(t)
        text = "\n\n".join(pages)
    except Exception as e:
        logger.warning("Failed to extract text from %s: %s", file_path, e)
        text = ""

    # 2) If Vertex libs not available, fallback to stub
    if aiplatform is None or service_account is None:
        logger.info("[embeddings-stub] libraries missing; queued stub job for %s (batch=%s) -> %s", file_path, batch_id, job_id)
        return job_id

    # 3) Prepare credentials and call Vertex (best-effort)
    project = os.environ.get("VERTEX_PROJECT")
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    model_id = os.environ.get("VERTEX_EMBEDDING_MODEL") or os.environ.get("VERTEX_MODEL_ID")

    try:
        creds: Any = None
        sa_json = os.environ.get("VERTEX_SERVICE_ACCOUNT_JSON")
        if sa_json:
            info = json.loads(sa_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/cloud-platform"])

        # Initialize aiplatform; if creds is None, SDK will use ADC
        if creds:
            aiplatform.init(project=project, location=location, credentials=creds)
        else:
            aiplatform.init(project=project, location=location)

        if not model_id:
            raise RuntimeError("No embedding model configured (set VERTEX_EMBEDDING_MODEL or VERTEX_MODEL_ID)")

        # Use the high-level TextEmbeddingModel API if available
        TextEmbeddingModel = getattr(aiplatform, 'TextEmbeddingModel', None) or getattr(getattr(aiplatform, 'models', None), 'TextEmbeddingModel', None)
        if TextEmbeddingModel is None:
            raise RuntimeError("TextEmbeddingModel is not available in the installed aiplatform SDK")

        model = TextEmbeddingModel.from_pretrained(model_id)
        # Note: for large PDFs you should chunk the text size appropriately before embedding
        resp = model.get_embeddings([text or ""])  # send one document

        # Normalize embeddings response into a plain list of vectors
        embeddings = []
        for item in resp:
            if hasattr(item, 'values'):
                embeddings.append(list(item.values))
            elif isinstance(item, dict) and 'embedding' in item:
                embeddings.append(item['embedding'])
            else:
                embeddings.append(item)

        # Persist embeddings near the uploads folder
        emb_dir = UPLOAD_BASE / Path(file_path).parent.name.replace('original', 'embeddings')
        emb_dir.mkdir(parents=True, exist_ok=True)
        emb_path = emb_dir / (Path(file_path).stem + '.emb.json')
        with emb_path.open('w', encoding='utf-8') as ef:
            json.dump({"batch_id": batch_id, "file": file_path, "embeddings": embeddings}, ef)

        logger.info("[embeddings] created embeddings for %s -> %s", file_path, emb_path)
        return job_id

    except Exception as e:
        logger.exception("Embedding pipeline failed for %s: %s", file_path, e)
        # Fall back to a queued-stub job id so the API remains successful
        return job_id


@app.post("/api/upload-batch")
async def upload_batch(batch_name: Optional[str] = Form(None), files: List[UploadFile] = File(...)):
    """Endpoint to upload multiple PDF resumes as a batch.

    Accepts multipart/form-data:
      - batch_name: optional string
      - files: one or more file uploads
    """
    # 1) Ensure files present
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(status_code=400, detail=f"Too many files. Max {MAX_FILES_PER_BATCH} allowed.")

    # 2) Ensure batch name
    if not batch_name:
        batch_name = f"batch-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    batch_id = str(uuid4())
    batch_dir = UPLOAD_BASE / batch_name / "original"
    batch_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for upload in files:
        # Basic file-type validation
        filename = Path(upload.filename).name
        if not filename.lower().endswith('.pdf') and upload.content_type != 'application/pdf':
            raise HTTPException(status_code=400, detail=f"Invalid file type for {filename}. Only PDFs allowed.")

        dest_path = batch_dir / filename

        try:
            # Save to disk
            saved = save_file_to_storage(upload, dest_path)
            size = saved.stat().st_size

            # Size validation
            if size > MAX_FILE_SIZE_BYTES:
                # cleanup
                try:
                    saved.unlink()
                except Exception:
                    pass
                raise HTTPException(status_code=400, detail=f"File {filename} exceeds max size {MAX_FILE_SIZE_BYTES} bytes")

            # Compute a safe storage path string. Prefer a path relative to the current
            # working directory for readability, but fall back to the absolute path if
            # relative computation fails (different mounts, symlinks, etc.).
            try:
                storage_path = os.path.relpath(saved, Path.cwd())
            except Exception:
                try:
                    storage_path = str(saved.resolve())
                except Exception:
                    storage_path = str(saved)

            saved_files.append({
                "filename": filename,
                "size": size,
                "storage_path": storage_path,
            })

            # 3) Kick off embeddings (stub)
            create_embeddings_for_pdf(str(saved), batch_id)

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to save uploaded file %s: %s", filename, e)
            raise HTTPException(status_code=500, detail=f"Failed to save file {filename}")

    # 4) Persist batch metadata as JSON
    metadata = {
        "batch_id": batch_id,
        "batch_name": batch_name,
        "uploaded_at": datetime.datetime.utcnow().isoformat() + 'Z',
        "files": saved_files,
        "uploader": None,
    }

    try:
        meta_path = UPLOAD_BASE / batch_name / "metadata.json"
        with meta_path.open("w", encoding="utf-8") as mf:
            json.dump(metadata, mf, indent=2)
    except Exception:
        logger.exception("Failed to write batch metadata for %s", batch_name)

    return {
        "success": True,
        "batchId": batch_id,
        "batchName": batch_name,
        "files": saved_files,
        "message": "Files uploaded and embedding jobs queued.",
    }



@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    # 1) (Optional) Generate Agora token if needed (demo)
    agora_token = generate_agora_token()

    # 2) Call Vertex AI (or mock)
    reply = call_vertex_ai(req.message)

    # 3) Return structured response
    return ChatResponse(reply=reply, source="vertex-ai + agora-placeholder")


@app.get("/agora/token")
async def agora_token_endpoint(uid: Optional[str] = None):
    """Simple endpoint to retrieve a server-generated Agora token (placeholder).

    Replace logic with Agora SDK token generator.
    """
    token = generate_agora_token(uid)
    return {"token": token}
