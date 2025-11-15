"""
RezumAI - Main API

Key points:
- Loads .env first (so modules that read env see correct values).
- Robust GCS / Firestore initialization (resolves absolute paths).
- Lifespan event initializes vertex_search (RAG clients).
- Exposes /api/chat, upload endpoints, and simple health checks.
"""
# pathlib.Path and dotenv are removed - not used in production.
import os
import logging
import uuid
from fastapi import status
from typing import Optional, List
from contextlib import asynccontextmanager

# -------------------------
# Load environment (FIRST)
# -------------------------
#
# !!! DEPLOYMENT NOTE !!!
# We do NOT load a .env file in a production environment.
# All configuration (PROJECT_ID, BUCKET_NAME, etc.)
# must be set as environment variables in the deployment service
# (e.g., Cloud Run, GKE, App Engine).
#
# try:
#     from dotenv import load_dotenv
#
#     env_path = Path(__file__).parent / ".env"
#     if env_path.exists():
#         print(f"Loading environment from: {env_path.resolve()}")
#         load_dotenv(env_path)
#     else:
#         print(".env file not found, relying on system environment.")
# except Exception as e:
#     print(f"Error loading .env file: {e}")
#

# Now imports that depend on env values
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import router that depends on env
from firestore import router as firestore_router  # must come after env load

# Import vertex_search (RAG / Matching Engine) AFTER env
import vertex_search

# Search integration: returns candidate dicts / formatting helpers
from chatbot_search_integration import search_candidates, format_candidate_for_chat

# Try to import google cloud storage (for upload endpoint)
try:
    from google.cloud import storage
    # We do NOT import service_account. We will use Application Default Credentials.
except Exception:
    storage = None

# -------------------------
# Configuration
# -------------------------
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
# GOOGLE_CREDS is no longer needed, we use ADC
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_SIZE_BYTES = int(os.getenv("MAX_SIZE_BYTES", 10 * 1024 * 1024))  # 10 MB default

logger = logging.getLogger("uvicorn.error")

# -------------------------
# Initialize GCS / Firestore clients (robust)
# -------------------------
storage_client = None
bucket = None

# _resolve_creds_path function is removed - we don't use file paths.

try:
    if storage is None:
        logger.warning("google-cloud-storage not installed; upload endpoints will be disabled.")
    else:
        # In a deployment, we rely on Application Default Credentials (ADC).
        # The service account is attached to the runtime environment (e.g., Cloud Run).
        # We only need the PROJECT_ID.
        if not PROJECT_ID:
            logger.critical("PROJECT_ID environment variable is not set. GCS client cannot be initialized.")
            raise ValueError("PROJECT_ID not set")

        # This call will automatically use the attached service account (ADC)
        storage_client = storage.Client(project=PROJECT_ID)

        if BUCKET_NAME:
            bucket = storage_client.bucket(BUCKET_NAME)
        else:
            logger.warning("BUCKET_NAME not set. /upload_resume will fail until configured.")
except Exception as e:
    logger.exception("Failed to initialize GCS client (using ADC): %s", e)
    storage_client = None
    bucket = None

# -------------------------
# FastAPI Lifespan: init RAG clients
# -------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI app starting up...")
    try:
        # This function must ALSO rely on ADC and not file-based auth
        vertex_search.initialize_globals()
        logger.info("Vertex/RAG clients initialized.")
    except Exception as e:
        logger.critical("FATAL: RAG client initialization failed: %s. API will have limited functionality.", e)
    yield
    logger.info("FastAPI app shutting down.")

app = FastAPI(title="RezumAI - RAG API", lifespan=lifespan)

# !!! SECURITY NOTE !!!
# allow_origins=["*"] is insecure for production.
# You MUST restrict this to your frontend's domain.
# e.g., allow_origins=["https://your-frontend.com"]
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
    _, dot, ext = filename.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""
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
        # This module must ALSO use ADC (no file-based auth)
        from firestore import _init_firestore_client  # local import to avoid circular issues
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
    Chat flow:
    1. Use vertex_search.find_neighbor_ids to get candidate datapoint ids (namespace-scoped by batch_tag/recruiter_uuid).
    2. Call search_candidates(...) to fetch/format candidate documents (search integration).
    3. Build context for the generative model from top candidates and call Gemini.
    4. Return generated answer with citations.
    """
    try:
        # 1) Find neighbors (vector search)
        try:
            neighbor_ids = vertex_search.find_neighbor_ids(
                query=request.query,
                batch_tag=request.batch_tag,
                top_k=15
            )
        except Exception as e:
            logger.exception("Vector search error: %s", e)
            neighbor_ids = []

        if not neighbor_ids:
            logger.info("No neighbors returned by vector search for batch=%s recruiter=%s", request.batch_tag, request.recruiter_uuid)
            return ChatResponse(content="I couldn't find any candidates matching your criteria in that batch.", citations=[])

        # 2) Use search integration to fetch candidate records
        # The search_candidates integration is expected to accept neighbor_ids or fallback to query-based search.
        # We'll try neighbor_ids first (most precise). If that fails, fallback to query-based call.
        candidates = []
        try:
            # try the neighbor_ids-first signature (common)
            candidates = search_candidates(neighbor_ids=neighbor_ids, recruiter_uuid=request.recruiter_uuid, batch_tag=request.batch_tag, top_k=10)
        except TypeError:
            # signature does not accept neighbor_ids -> fallback to query-based call
            try:
                candidates = search_candidates(query=request.query, recruiter_uuid=request.recruiter_uuid, batch_tag=request.batch_tag, top_k=10)
            except Exception as e:
                logger.exception("search_candidates fallback failed: %s", e)
                candidates = []
        except Exception as e:
            logger.exception("search_candidates failed: %s", e)
            candidates = []

        if not candidates:
            logger.info("No candidate documents retrieved after search integration.")
            return ChatResponse(content="I found some potential matches, but none were relevant after review.", citations=[])

        # 3) Prepare context and citations. Use format_candidate_for_chat if available to normalize display.
        context_parts = []
        citations = []
        top_candidates = candidates[:10]  # limit to top-10 for prompt size

        for i, c in enumerate(top_candidates):
            try:
                formatted = format_candidate_for_chat(c) if callable(format_candidate_for_chat) else c
            except Exception:
                # If formatting fails, fall back to raw candidate dict
                logger.exception("format_candidate_for_chat failed for candidate: %s", c.get("candidate_id") if isinstance(c, dict) else None)
                formatted = c

            # Build a compact textual snippet for the context (fields tolerant)
            name = formatted.get("name") or formatted.get("candidate_name") or formatted.get("candidateName") or formatted.get("candidate_id") or "Unknown"
            summary = formatted.get("summary") or formatted.get("profile_summary") or formatted.get("summary_text") or ""

            context_parts.append(
                f"--- Candidate {i+1} ---\nName: {name}\nSummary: {summary}\n"
            )

            # Ensure we map candidate id -> citation candidateId
            cand_id = formatted.get("candidate_id") or formatted.get("id") or formatted.get("candidateId") or None
            citations.append(Citation(
                candidateId=str(cand_id) if cand_id else f"cand_{i}",
                candidateName=name,
                snippet=(summary[:150] + "...") if summary else ""
            ))

        context = "\n\n".join(context_parts)

        # 4) Build prompt
        prompt = f"""You are an expert AI recruitment assistant. Your task is to answer the user's question based *only* on the candidate summaries provided in the 'Context'.

CONTEXT:
{context}

USER'S QUESTION:
{request.query}

Based on the context, provide a helpful and concise answer. If the context does not contain the answer, say so.
Do not mention "based on the context" in your final answer.
"""

        # 5) Generate with Gemini (support async and sync call shapes)
        if not getattr(vertex_search, "gen_model", None):
            logger.error("Generative model not initialized in vertex_search.")
            raise HTTPException(status_code=500, detail="Generative model not initialized")

        # Try async generator if available
        try:
            # many newer SDKs expose generate_content_async / generate_async / generate_content
            if hasattr(vertex_search.gen_model, "generate_content_async"):
                gemini_response = await vertex_search.gen_model.generate_content_async(prompt)
                text = getattr(gemini_response, "text", str(gemini_response)).strip()
            elif hasattr(vertex_search.gen_model, "generate_async"):
                gemini_response = await vertex_search.gen_model.generate_async(prompt)
                text = getattr(gemini_response, "text", str(gemini_response)).strip()
            else:
                # fallback to synchronous call (SDK may provide generate or generate_content)
                try:
                    gemini_response = vertex_search.gen_model.generate(prompt)
                    text = getattr(gemini_response, "text", str(gemini_response)).strip()
                except Exception:
                    # last-resort REST-style call wrapper (if the object expects generate_content)
                    gemini_response = vertex_search.gen_model.generate_content(prompt)
                    text = getattr(gemini_response, "text", str(gemini_response)).strip()
        except Exception as e:
            logger.exception("Generative model call failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Generative model invocation failed: {e}")

        return ChatResponse(content=text, citations=citations)

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
                "and the runtime service account has 'Storage Object Creator' permissions."
            ),
        )

    orig_name = original_filename or file.filename or "resume"
    safe_name = _secure_filename(orig_name)
    _, dot, ext = safe_name.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""

    size = 0
    try:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    except Exception:
        size = 0

    validation_err = _validate_extension_and_size(safe_name, size)
    if validation_err:
        raise HTTPException(status_code=400, detail=validation_err)

    session_id = str(uuid.uuid4())
    gcs_filename = f"{session_id}{ext}"
    gcs_path = f"{recruiter_uuid}/{batch_name}/{gcs_filename}"
    blob = bucket.blob(gcs_path)

    try:
        if blob.exists():
            raise HTTPException(status_code=409, detail="A file with this name already exists in this batch.")

        file.file.seek(0)
        blob.upload_from_file(file.file, content_type=file.content_type)

        # Patch metadata (best-effort)
        try:
            blob.metadata = {
                "recruiter_uuid": recruiter_uuid,
                "batch_name": batch_name,
                "original_filename": safe_name,
                "session_id": session_id,
            }
            blob.patch()
        except Exception:
            logger.exception("Failed to patch blob metadata for %s", gcs_path)

        # Write to Firestore using vertex_search.firestore_client if available
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

        return JSONResponse(status_code=201, content={
            "session_id": session_id,
            "bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed for %s: %s", gcs_path, e)
        # Best-effort cleanup
        try:
            bucket.blob(gcs_path).delete()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")