"""
FastAPI service (v2): Upload resumes to GCS and record metadata in Firestore.

Changes from previous version:
- Each recruiter has a UUID (recruiter_uuid) used as the top-level folder.
- Recruiter chooses a batch name (batch_name) which becomes a subfolder under the recruiter UUID.
  Path layout: <recruiter_uuid>/<batch_name>/<session_id>.<ext>
- Cloud Function is NOT invoked via HTTP; it auto-triggers on new GCS uploads.

Behaviour:
- Accepts multipart form file + recruiter_uuid + batch_name + optional original_filename.
- Generates session_id (UUID4) for each upload.
- Uploads file to GCS bucket (configured via env var BUCKET_NAME).
- Writes a metadata document to Firestore collection `recruiter_uploads` keyed by session_id.

Environment variables:
- GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json (or rely on default credentials)
- BUCKET_NAME=your-gcs-bucket-name

IAM roles required for the service account used:
- storage.objects.create
- firestore.documents.create / firestore.documents.update

Run with:
uvicorn fastapi_resume_upload_v2:app --host 0.0.0.0 --port 8000
"""

import os
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage, firestore
from google.oauth2 import service_account

# Configuration from env
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
app = FastAPI(title="RezumAI Resume Upload API v2")


def _secure_filename(name: str) -> str:
    # minimal sanitization - adapt as needed
    return name.replace("..", "").replace("/", "_")


@app.post("/upload_resume")
async def upload_resume(
    recruiter_uuid: str = Form(...),
    batch_name: str = Form(...),
    original_filename: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Upload a resume file, store in GCS, add Firestore metadata."""

    # Basic validation
    if not recruiter_uuid:
        raise HTTPException(status_code=400, detail="recruiter_uuid is required")
    if not batch_name:
        raise HTTPException(status_code=400, detail="batch_name is required")

    session_id = str(uuid.uuid4())

    # Determine extension
    orig_name = original_filename or file.filename or "resume"
    safe_name = _secure_filename(orig_name)
    _, dot, ext = safe_name.rpartition(".")
    ext = f".{ext}" if dot else ""

    # GCS path per recruiter UUID and batch name
    gcs_path = f"{recruiter_uuid}/{batch_name}/{safe_name}"

    try:
        blob = bucket.blob(gcs_path)
        # prevent duplicate uploads
        if blob.exists():
            raise HTTPException(status_code=409, detail="A file with this name already exists in this batch.")
        file.file.seek(0)
        blob.upload_from_file(file.file, content_type=file.content_type)

        # Set metadata on the GCS object
        blob.metadata = {
            
            "recruiter_uuid": recruiter_uuid,
            "batch_name": batch_name,
            "original_filename": safe_name,
        }
        blob.patch()

        # Firestore storage handled automatically by Cloud Function
        # (metadata writing removed here)

        return JSONResponse(status_code=201, content={
            "session_id": session_id,
            "bucket": BUCKET_NAME,
            "gcs_path": gcs_path,
        })

    except Exception as e:
        # cleanup on failure
        try:
            bucket.blob(gcs_path).delete()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Example curl (replace values):
# curl -X POST http://localhost:8000/upload_resume \
#   -F "recruiter_uuid=rec-uuid-1234" \
#   -F "batch_name=acme_hiring_batch_2025" \
#   -F "original_filename=Alice_Resume.pdf" \
#   -F "file=@/path/to/Alice_Resume.pdf"
