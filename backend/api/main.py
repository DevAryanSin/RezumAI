# main.py
"""
RezumAI - Resume upload API (robust)

Features:
- Loads .env (if present).
- Works when google-cloud libs / env are missing (upload endpoint will return 500 with clear message).
- POST /upload_resume accepts multipart form (recruiter_uuid, batch_name, optional original_filename, file).
- Generates session_id for each upload and stores object at:
    <recruiter_uuid>/<batch_name>/<session_id><ext>
- Optionally writes Firestore metadata if credentials + Firestore available.
- GET /upload_resume serves a small test HTML form (prevents 405 when you open the URL in a browser).
- /favicon.ico returns 204 (silences favicon 404s).
"""
from firestore import router as firestore_router
from pathlib import Path
import os
import logging
import uuid
from typing import Optional

# optional dotenv
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# Try to import google cloud storage and firestore; set to None if unavailable
try:
    from google.cloud import storage  # type: ignore
    from google.cloud import firestore  # type: ignore
    from google.oauth2 import service_account  # type: ignore
except Exception:
    storage = None  # type: ignore
    firestore = None  # type: ignore
    service_account = None  # type: ignore

# --- Configuration ---
BUCKET_NAME = os.getenv("BUCKET_NAME")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_SIZE_BYTES = int(os.getenv("MAX_SIZE_BYTES", 10 * 1024 * 1024))  # default 10MB

logger = logging.getLogger("uvicorn.error")

# --- Initialize GCP clients if possible ---
storage_client = None
bucket = None
firestore_client = None
if storage is None:
    logger.warning("google-cloud-storage not available; uploads disabled until configured.")
else:
    try:
        if GOOGLE_CREDS and service_account:
            creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS)
            storage_client = storage.Client(credentials=creds)
            if firestore is not None:
                firestore_client = firestore.Client(credentials=creds)
        else:
            storage_client = storage.Client()
            if firestore is not None:
                firestore_client = firestore.Client()
        if BUCKET_NAME:
            bucket = storage_client.bucket(BUCKET_NAME)
        else:
            logger.warning("BUCKET_NAME not set. Upload endpoint will return an error until configured.")
    except Exception as e:
        logger.exception("Failed to initialize GCS/Firestore clients: %s", e)
        storage_client = None
        bucket = None
        firestore_client = None

app = FastAPI(title="RezumAI - Resume Upload API (robust)")

# CORS for development; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(firestore_router, prefix="/api")


def _secure_filename(name: str) -> str:
    # minimal sanitization
    return name.replace("..", "").replace("/", "_")


def _validate_extension_and_size(filename: str, size: int) -> Optional[str]:
    _, dot, ext = filename.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if size > MAX_SIZE_BYTES:
        return f"File too large. Max size is {MAX_SIZE_BYTES // (1024 * 1024)} MB."
    return None


@app.get("/favicon.ico")
def favicon():
    # Return no content to prevent 404 favicon noise from browsers
    return Response(status_code=204)


@app.get("/upload_resume", response_class=HTMLResponse)
def upload_form():
    # Simple debugging form so opening the endpoint in a browser doesn't produce 405
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
    """
    Upload resume file to GCS and optionally write Firestore metadata.
    Produces a session_id and stores object at:
    <recruiter_uuid>/<batch_name>/<session_id><ext>
    """
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
                "and GOOGLE_APPLICATION_CREDENTIALS points to a valid service-account JSON if required.\n"
                "Example (PowerShell):\n"
                "$env:BUCKET_NAME='my-bucket'; $env:GOOGLE_APPLICATION_CREDENTIALS='C:\\path\\sa.json'; python -m uvicorn main:app --reload\n"
            ),
        )

    # prepare names
    orig_name = original_filename or file.filename or "resume"
    safe_name = _secure_filename(orig_name)

    # determine extension
    _, dot, ext = safe_name.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""

    # attempt to compute size. If not possible, set to 0 and rely on GCS limits.
    size = 0
    try:
        # Seek to end to get size for file-like objects
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
        # Check duplicates by path (we use session_id in filename so collision is extremely unlikely;
        # but keep check for safety if you later switch naming)
        if blob.exists():
            raise HTTPException(status_code=409, detail="A file with this name already exists in this batch.")

        # Upload
        file.file.seek(0)
        blob.upload_from_file(file.file, content_type=file.content_type)

        # Attach metadata
        try:
            blob.metadata = {
                "recruiter_uuid": recruiter_uuid,
                "batch_name": batch_name,
                "original_filename": safe_name,
                "session_id": session_id,
            }
            blob.patch()
        except Exception:
            # non-fatal; continue
            logger.exception("Failed to patch metadata for blob %s", gcs_path)

        # Optionally write a Firestore document if client available.
        if firestore_client is not None:
            try:
                doc_ref = firestore_client.collection("recruiter_uploads").document(session_id)
                doc_ref.set({
                    "recruiter_uuid": recruiter_uuid,
                    "batch_name": batch_name,
                    "original_filename": safe_name,
                    "session_id": session_id,
                    "bucket": BUCKET_NAME,
                    "gcs_path": gcs_path,
                    "content_type": file.content_type,
                    "size_bytes": size,
                    "uploaded_at": firestore.SERVER_TIMESTAMP,
                })
            except Exception:
                logger.exception("Failed to write metadata to Firestore for session %s", session_id)
                # do not fail the upload because of metadata write problem

        return JSONResponse(status_code=201, content={
            "session_id": session_id,
            "bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed for %s: %s", gcs_path, e)
        # Best effort cleanup
        try:
            bucket.blob(gcs_path).delete()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
