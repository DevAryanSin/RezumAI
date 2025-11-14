"""
Main FastAPI application consolidating all endpoints for RezumAI upload flow.

Endpoints included:
- POST /create_recruiter -> creates a recruiter_id (UUID) and a recruiters/{id} doc
- GET  /recruiter/{recruiter_id}/batches -> returns list of batches for the recruiter
- POST /upload_resume -> upload file to GCS and record metadata (same behavior as original)
- GET  /healthz -> simple health check

Notes:
- Expects environment variable BUCKET_NAME and optional GOOGLE_APPLICATION_CREDENTIALS.
- Uploads add the batch name to recruiters/{id}.batches via Firestore ArrayUnion for fast lookup.
- Firestore collections used: "recruiter_uploads" and "recruiters"

Run with:
uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import uuid
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage, firestore
from google.oauth2 import service_account

# Configuration
BUCKET_NAME = os.getenv("BUCKET_NAME")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Initialize GCP clients
if GOOGLE_CREDS:
    creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS)
    storage_client = storage.Client(credentials=creds)
    firestore_client = firestore.Client(credentials=creds)
else:
    storage_client = storage.Client()
    firestore_client = firestore.Client()

if not BUCKET_NAME:
    raise RuntimeError("Environment variable BUCKET_NAME is required")

bucket = storage_client.bucket(BUCKET_NAME)
app = FastAPI(title="RezumAI - Main API")


def _secure_filename(name: str) -> str:
    return name.replace("..", "").replace("/", "_")


@app.post("/create_recruiter")
def create_recruiter():
    """Create a recruiter record and return recruiter_id (uuid)."""
    recruiter_id = str(uuid.uuid4())
    doc = {
        "recruiter_id": recruiter_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        "batches": [],
    }
    firestore_client.collection("recruiters").document(recruiter_id).set(doc)
    return {"recruiter_id": recruiter_id}


@app.get("/recruiter/{recruiter_id}/batches")
def list_batches(recruiter_id: str) -> List[str]:
    """Return known batch names for a recruiter.

    Priority:
    1. If recruiters/{id} document has `batches` array, return it.
    2. Otherwise, scan recruiter_uploads for distinct branch_id values.
    """
    # Try to read the recruiter doc first
    doc_ref = firestore_client.collection("recruiters").document(recruiter_id)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        batches = data.get("batches") or []
        if batches:
            return batches

    # Fallback: scan recruiter_uploads collection for this recruiter
    coll = firestore_client.collection("recruiter_uploads")
    q = coll.where("recruiter_id", "==", recruiter_id).stream()
    seen = set()
    batches = []
    for d in q:
        dd = d.to_dict() or {}
        b = dd.get("branch_id") or dd.get("batch_name")
        if b and b not in seen:
            seen.add(b)
            batches.append(b)
            if len(batches) >= 100:
                break
    return batches


@app.post("/upload_resume")
async def upload_resume(
    recruiter_id: str = Form(...),
    branch_id: str = Form(...),
    original_filename: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Upload a resume file, store in GCS, add Firestore metadata, and record batch on recruiter doc."""

    if not recruiter_id:
        raise HTTPException(status_code=400, detail="recruiter_id is required")
    if not branch_id:
        raise HTTPException(status_code=400, detail="branch_id is required")

    session_id = str(uuid.uuid4())
    orig_name = original_filename or file.filename or "resume"
    safe_name = _secure_filename(orig_name)
    _, dot, ext = safe_name.rpartition(".")
    ext = f".{ext}" if dot else ""

    gcs_path = f"{recruiter_id}/{branch_id}/{session_id}{ext}"

    try:
        blob = bucket.blob(gcs_path)
        file.file.seek(0)
        blob.upload_from_file(file.file, content_type=file.content_type)

        blob.metadata = {
            "session_id": session_id,
            "recruiter_id": recruiter_id,
            "branch_id": branch_id,
            "original_filename": safe_name,
        }
        blob.patch()

        # Save metadata to Firestore
        doc_ref = firestore_client.collection("recruiter_uploads").document(session_id)
        metadata = {
            "session_id": session_id,
            "recruiter_id": recruiter_id,
            "branch_id": branch_id,
            "gcs_bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
            "original_filename": safe_name,
            "content_type": file.content_type,
            "size_bytes": blob.size,
            "uploaded_at": firestore.SERVER_TIMESTAMP,
        }
        doc_ref.set(metadata)

        # Add branch_id to recruiters/{recruiter_id}.batches via ArrayUnion for fast lookup
        try:
            firestore_client.collection("recruiters").document(recruiter_id).set(
                {"batches": firestore.ArrayUnion([branch_id])}, merge=True
            )
        except Exception:
            # non-critical — continue even if we can't update batches
            pass

        return JSONResponse(status_code=201, content={
            "session_id": session_id,
            "bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
        })

    except Exception as e:
        try:
            bucket.blob(gcs_path).delete()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
