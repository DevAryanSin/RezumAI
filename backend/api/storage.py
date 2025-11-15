import os
import time
from typing import Optional
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET") or os.getenv("BUCKET_NAME")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
RESUMES_PREFIX = os.getenv("GCS_RESUMES_PREFIX", "resumes/").rstrip("/") + "/"

_storage_client: Optional[storage.Client] = None
_bucket: Optional[storage.Bucket] = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        if GOOGLE_CREDS:
            # Resolve relative paths relative to the api directory
            if not os.path.isabs(GOOGLE_CREDS):
                creds_path = Path(__file__).parent / GOOGLE_CREDS
            else:
                creds_path = Path(GOOGLE_CREDS)
            
            if creds_path.exists():
                creds = service_account.Credentials.from_service_account_file(str(creds_path))
                _storage_client = storage.Client(credentials=creds, project=PROJECT_ID)
            else:
                raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        else:
            # Use application default credentials
            _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def get_bucket() -> storage.Bucket:
    global _bucket
    if _bucket is None:
        client = get_storage_client()
        if not BUCKET_NAME:
            raise RuntimeError("GCS bucket not configured. Set GCS_BUCKET or BUCKET_NAME")
        _bucket = client.bucket(BUCKET_NAME)
    return _bucket


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=6),
       retry=retry_if_exception_type(Exception))
def upload_bytes(path: str, data: bytes, content_type: str = "application/pdf") -> str:
    bucket = get_bucket()
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return path


def generate_signed_url(path: str, expires_seconds: int = 3600) -> str:
    bucket = get_bucket()
    blob = bucket.blob(path)
    return blob.generate_signed_url(expiration=expires_seconds, method="GET")


def build_resume_path(batch_id: str, candidate_id: str) -> str:
    return f"{RESUMES_PREFIX}{batch_id}/{candidate_id}.pdf"
