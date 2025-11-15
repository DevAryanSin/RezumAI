# main.py
"""
RezumAI - Main API

Key points:
- Loads .env first (so modules that read env see correct values).
- Robust GCS / Firestore initialization (resolves absolute paths).
- Lifespan event initializes vertex_search (RAG clients).
- Exposes /api/chat, upload endpoints, and simple health checks.
"""
from pathlib import Path
import os
import logging
import uuid
from fastapi import status
from typing import Optional, List
from contextlib import asynccontextmanager

# -------------------------
# Load environment (FIRST)
# -------------------------
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        print(f"Loading environment from: {env_path.resolve()}")
        load_dotenv(env_path)
    else:
        print(".env file not found, relying on system environment.")
except Exception as e:
    print(f"Error loading .env file: {e}")

# Now imports that depend on env values
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import router that depends on env
from .firestore import router as firestore_router  # must come after env load

# Import vertex_search (RAG / Matching Engine) AFTER env
from . import vertex_search

# New modular helpers for storage, PDF processing, embeddings, and chat
from .storage import upload_bytes, build_resume_path, generate_signed_url
from .pdf_utils import extract_text_from_pdf, chunk_text
from .embeddings import embed_texts, upsert_chunks_firestore
from .chat import answer_query

# Search integration: returns candidate dicts / formatting helpers
from .chatbot_search_integration import search_candidates, format_candidate_for_chat

# Try to import google cloud storage (for upload endpoint)
try:
    from google.cloud import storage
    from google.oauth2 import service_account
except Exception:
    storage = None
    service_account = None

# -------------------------
# Configuration
# -------------------------
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_SIZE_BYTES = int(os.getenv("MAX_SIZE_BYTES", 10 * 1024 * 1024))  # 10 MB default

logger = logging.getLogger("uvicorn.error")

# -------------------------
# Initialize GCS / Firestore clients (robust)
# -------------------------
storage_client = None
bucket = None

def _resolve_creds_path(creds_path: Optional[str]) -> Optional[str]:
    if not creds_path:
        return None
    return os.path.abspath(creds_path)

try:
    if storage is None:
        logger.warning("google-cloud-storage not installed; upload endpoints will be disabled.")
    else:
        creds_path = _resolve_creds_path(GOOGLE_CREDS)
        if creds_path:
            if not os.path.exists(creds_path):
                logger.error("GOOGLE_APPLICATION_CREDENTIALS file not found at: %s", creds_path)
                raise FileNotFoundError(f"GOOGLE_APPLICATION_CREDENTIALS not found: {creds_path}")
            creds = service_account.Credentials.from_service_account_file(creds_path) if service_account else None
            storage_client = storage.Client(credentials=creds, project=PROJECT_ID) if creds else storage.Client(project=PROJECT_ID)
        else:
            # Use ADC / default credentials
            storage_client = storage.Client(project=PROJECT_ID)

        if BUCKET_NAME:
            bucket = storage_client.bucket(BUCKET_NAME)
        else:
            logger.warning("BUCKET_NAME not set. /upload_resume will fail until configured.")
except Exception as e:
    logger.exception("Failed to initialize GCS client: %s", e)
    storage_client = None
    bucket = None

# -------------------------
# FastAPI Lifespan: init RAG clients
# -------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI app starting up...")
    try:
        vertex_search.initialize_globals()
        logger.info("Vertex/RAG clients initialized.")
    except Exception as e:
        logger.critical("FATAL: RAG client initialization failed: %s. API will have limited functionality.", e)
    yield
    logger.info("FastAPI app shutting down.")

app = FastAPI(title="RezumAI - RAG API", lifespan=lifespan)

# CORS (dev-friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the Firestore router (read-only API)
app.include_router(firestore_router, prefix="/api")

# -------------------------
# Pydantic models for chat
# -------------------------
class ChatRequest(BaseModel):
    query: str
    recruiter_uuid: str
    batch_tag: str

class Citation(BaseModel):
    candidateId: str
    candidateName: str
    snippet: str

class ChatResponse(BaseModel):
    content: str
    citations: List[Citation]

# -------------------------
# Utility helpers
# -------------------------
def _secure_filename(name: str) -> str:
    return name.replace("..", "").replace("/", "_")

def _validate_extension_and_size(filename: str, size: int) -> Optional[str]:
    # Normalize filename -> use basename and strip whitespace to avoid CRLF/space issues
    try:
        from pathlib import Path as _P
        filename = _P(filename).name
    except Exception:
        filename = filename
    filename = filename.strip()
    _, dot, ext = filename.rpartition(".")
    ext = ext.strip().lower()
    ext = f".{ext}" if dot else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if size > MAX_SIZE_BYTES:
        return f"File too large. Max size is {MAX_SIZE_BYTES // (1024 * 1024)} MB."
    return None

# -------------------------
# Simple endpoints
# -------------------------
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/api/health/firestore")
def health_firestore():
    """
    Quick health check for Firestore connectivity (calls router's init).
    Useful for debugging environment/credentials.
    """
    try:
        # Call into firestore module's initializer to ensure client is up
        from .firestore import _init_firestore_client  # local import to avoid circular issues
        db = _init_firestore_client()
        # cheap call
        collections = list(db.collections())
        return {"ok": True, "collections_count": len(collections)}
    except Exception as e:
        logger.exception("Firestore health check failed: %s", e)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

# -------------------------
# Chat endpoint (RAG)
# -------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    """
    Simplified chat flow: use embeddings + Firestore KNN + Gemini synthesis
    via chat.answer_query(batch_id, query). Maintains existing request shape.
    """
    try:
        result = await answer_query(batch_id=request.batch_tag, query=request.query)
        return ChatResponse(content=result.get("answer", ""), citations=[])
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /api/chat endpoint: %s", e)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

# -------------------------
# Upload endpoints (minimal)
# -------------------------
@app.get("/upload_resume", response_class=HTMLResponse)
def upload_form():
    html = """
    <!doctype html>
    <html>
    <head><meta charset="utf-8"><title>Upload Resume (test form)</title></head>
    <body>
        <h3>Upload Resume (test)</h3>
        <form action="/upload_resume" enctype="multipart/form-data" method="post">
        <label>recruiter_uuid: <input name="recruiter_uuid" value="rec-uuid-test"></label><br/>
        <label>batch_name: <input name="batch_name" value="batch_test"></label><br/>
        <label>original_filename (optional): <input name="original_filename" value=""></label><br/>
        <input name="file" type="file" /><br/><br/>
        <input type="submit" value="Upload" />
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/upload_resume")
async def upload_resume(
    recruiter_uuid: str = Form(...),
    batch_name: str = Form(...),
    original_filename: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    # Basic validation
    if not recruiter_uuid:
        raise HTTPException(status_code=400, detail="recruiter_uuid is required")
    if not batch_name:
        raise HTTPException(status_code=400, detail="batch_name is required")

    # Ensure storage configured
    if storage is None or storage_client is None or bucket is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Storage not configured. Ensure google-cloud-storage is installed, BUCKET_NAME is set, "
                "and GOOGLE_APPLICATION_CREDENTIALS points to a valid service-account JSON if required."
            ),
        )

    orig_name = original_filename or file.filename or "resume"
    safe_name = _secure_filename(orig_name)
    _, dot, ext = safe_name.rpartition(".")
    ext = ext.strip().lower()
    ext = f".{ext}" if dot else ""

    size = 0
    try:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    except Exception:
        size = 0

    validation_err = _validate_extension_and_size(safe_name, size)
    if validation_err:
        # Log helpful debug info to diagnose why extension check failed
        try:
            logger.info("Upload validation failed: %s", validation_err)
            logger.info("  orig_name=%r", orig_name)
            logger.info("  file.filename=%r", getattr(file, 'filename', None))
            logger.info("  file.content_type=%r", getattr(file, 'content_type', None))
            logger.info("  computed safe_name=%r", safe_name)
            logger.info("  computed ext=%r", ext)
        except Exception:
            pass

        raise HTTPException(status_code=400, detail=validation_err)

    session_id = str(uuid.uuid4())
    # Use session id as candidate id if none supplied by upstream
    candidate_id = session_id
    batch_id = batch_name
    gcs_path = build_resume_path(batch_id, candidate_id)

    try:
        # Upload to GCS directly via helper
        file.file.seek(0)
        data = file.file.read()
        upload_bytes(gcs_path, data, content_type=file.content_type or "application/pdf")

        # Best-effort metadata record in Firestore (upload log)
        try:
            if getattr(vertex_search, "firestore_client", None):
                doc_ref = vertex_search.firestore_client.collection("recruiter_uploads").document(session_id)
                doc_ref.set({
                    "recruiter_uuid": recruiter_uuid,
                    "batch_name": batch_name,
                    "original_filename": safe_name,
                    "session_id": session_id,
                    "bucket": BUCKET_NAME,
                    "gcs_path": gcs_path,
                    "content_type": file.content_type,
                    "size_bytes": size,
                    "uploaded_at": vertex_search.firestore.SERVER_TIMESTAMP if getattr(vertex_search, "firestore", None) else None,
                })
        except Exception:
            logger.exception("Failed to write metadata to Firestore for session %s", session_id)

        # Extract -> chunk -> embed -> upsert to resume_chunks
        text = extract_text_from_pdf(data)
        chunks = chunk_text(text)
        if chunks:
            vectors = embed_texts(chunks)
            upsert_chunks_firestore(batch_id=batch_id, candidate_id=candidate_id, chunks=chunks, vectors=vectors)

        signed_url = generate_signed_url(gcs_path)
        return JSONResponse(status_code=201, content={
            "session_id": session_id,
            "bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
            "signed_url": signed_url,
            "chunks_indexed": len(chunks) if chunks else 0,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed for %s: %s", gcs_path, e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
