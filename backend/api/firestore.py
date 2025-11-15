"""
Firestore API router for frontend consumption (read-only, with server-side remapping)

This router is read-only and performs server-side mapping so your existing
Firestore documents (created by your Cloud Function) are returned in the
shape expected by the frontend `CandidateCard` and `CandidateList`.

It tolerates missing credentials at import time (lazy init). If Firestore is
not available the endpoints return HTTP 500 with a clear message.

Mapping rules (heuristic):
- `candidate_id`, `recruiter_uuid`, `batch_tag`, `resume_gcs_url` are preserved.
- `name` is taken from document `name`.
- `title` and `currentCompany` are taken from the first `work_experience` entry if present.
- `skills` is copied from `skills`.
- `highlights` is empty unless present in doc.
- `snippets` is synthesized from: summary, first 2 work experience descriptions, first project.
- `experienceYears` is computed approximately from years present in work_experience start/end dates (best-effort).
- `tags` and `shortlisted` are passed through if present.

Place this file next to your `main.py` and include with `app.include_router(firestore_router, prefix="/api")`.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import os
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Configuration ---
CANDIDATE_COLLECTION = os.getenv("CANDIDATE_COLLECTION", "candidates")
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 20))
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Firestore lazy client objects
_db = None
_firestore_module = None
_firestore_error_msg = (
    "Firestore client not available. Ensure google-cloud-firestore is installed and "
    "GOOGLE_APPLICATION_CREDENTIALS is set to a service-account JSON path, or Application Default Credentials are available."
)

# --- Pydantic models (frontend shape) ---
class ResumeSchema(BaseModel):
    candidate_id: Optional[str] = None
    recruiter_uuid: Optional[str] = None
    batch_tag: Optional[str] = None
    resume_gcs_url: Optional[str] = None

    name: str = ""
    title: Optional[str] = ""
    currentCompany: Optional[str] = ""
    location: Optional[str] = ""
    score: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    snippets: List[Dict[str, str]] = Field(default_factory=list)
    experienceYears: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    shortlisted: Optional[bool] = False

router = APIRouter(
    prefix="",
    tags=["firestore"]
)

# --- Helpers ---

def _init_firestore_client():
    global _db, _firestore_module
    if _db is not None:
        return _db

    try:
        import google.auth
        from google.oauth2 import service_account
        from google.cloud import firestore as _firestore

        _firestore_module = _firestore

        if GOOGLE_CREDS and os.path.isfile(GOOGLE_CREDS):
            creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS)
            _db = _firestore.Client(credentials=creds)
        else:
            _db = _firestore.Client()

        return _db
    except Exception as e:
        logger.exception("Failed to initialize Firestore client: %s", e)
        raise HTTPException(status_code=500, detail=_firestore_error_msg + f" Details: {e}")


def _serialize_value(v: Any):
    try:
        if hasattr(v, "ToDatetime"):
            return v.ToDatetime().isoformat()
        if hasattr(v, "to_datetime"):
            return v.to_datetime().isoformat()
    except Exception:
        pass
    return v


def _compute_experience_years(work_experience: List[Dict[str, Any]]) -> float:
    """Best-effort compute total years of experience from start/end date strings.
    Looks for 4-digit years in start_date/end_date. If end_date contains 'present' or similar,
    uses current year. Returns a float with 1-decimal precision."""
    years = []
    current_year = datetime.utcnow().year
    for job in work_experience or []:
        s = job.get("start_date", "") or ""
        e = job.get("end_date", "") or ""
        start_years = re.findall(r"(19|20)\d{2}", s)
        end_years = re.findall(r"(19|20)\d{2}", e)
        try:
            start = int(start_years[0]) if start_years else None
            end = None
            if "present" in e.lower() or "current" in e.lower() or not e:
                end = current_year
            elif end_years:
                end = int(end_years[0])
            if start and end and end >= start:
                years.append(end - start)
        except Exception:
            continue
    if not years:
        return 0.0
    total = sum(years)
    # return approximate average or total? choose max(total, 0)
    return round(float(total), 1)


def synthesize_snippets(parsed_doc: Dict[str, Any], limit: int = 2) -> List[Dict[str, str]]:
    snippets = []
    # 1. summary
    summary = parsed_doc.get("summary")
    if summary:
        snippets.append({"text": summary})
    # 2. first N work descriptions
    we = parsed_doc.get("work_experience") or []
    for job in we[:limit]:
        desc = job.get("description")
        if desc:
            snippets.append({"text": desc})
    # 3. first project description
    projects = parsed_doc.get("projects") or []
    if projects:
        p = projects[0]
        if p.get("description"):
            snippets.append({"text": p.get("description")})
    # limit overall
    return snippets[:4]


def map_firestore_to_frontend(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map the stored Firestore document (from your Cloud Function) to the
    frontend ResumeSchema shape expected by CandidateCard.

    This is intentionally forgiving — missing fields are tolerated.
    """
    mapped: Dict[str, Any] = {}

    # passthrough ids + meta
    mapped["candidate_id"] = raw.get("candidate_id") or raw.get("id")
    mapped["recruiter_uuid"] = raw.get("recruiter_uuid")
    mapped["batch_tag"] = raw.get("batch_tag")
    mapped["resume_gcs_url"] = raw.get("resume_gcs_url")

    # basic fields
    mapped["name"] = raw.get("name", "")
    # pick title/company from first work_experience if available
    first_job = None
    we = raw.get("work_experience") or []
    if isinstance(we, list) and len(we) > 0:
        first_job = we[0]
    if first_job and isinstance(first_job, dict):
        mapped["title"] = first_job.get("title") or raw.get("title") or ""
        mapped["currentCompany"] = first_job.get("company") or raw.get("currentCompany") or ""
    else:
        mapped["title"] = raw.get("title") or ""
        mapped["currentCompany"] = raw.get("currentCompany") or ""

    mapped["location"] = raw.get("location") or ""
    mapped["score"] = raw.get("score")
    mapped["skills"] = raw.get("skills") or []
    mapped["highlights"] = raw.get("highlights") or []
    mapped["tags"] = raw.get("tags") or []
    mapped["shortlisted"] = bool(raw.get("shortlisted"))

    # snippets synthesis
    mapped["snippets"] = synthesize_snippets(raw, limit=2)

    # experience years best-effort computation
    mapped["experienceYears"] = _compute_experience_years(we)

    # Fallbacks in case some fields live under different keys (from earlier ingestion)
    # e.g., some docs may have 'projects' as list of dicts, 'summary' field, etc.

    return mapped


def doc_to_resume(doc) -> Dict[str, Any]:
    if not doc.exists:
        return {}
    raw = doc.to_dict() or {}
    # ensure candidate_id present
    if "candidate_id" not in raw:
        raw["candidate_id"] = doc.id

    # Map to frontend shape
    try:
        mapped = map_firestore_to_frontend(raw)
    except Exception as e:
        logger.exception("Error mapping Firestore doc %s: %s", doc.id, e)
        # fallback to raw doc
        mapped = raw

    # Ensure candidate_id present on mapped
    if "candidate_id" not in mapped or not mapped.get("candidate_id"):
        mapped["candidate_id"] = doc.id

    return mapped

# --- Routes (read-only) ---

@router.get("/candidates", response_model=List[ResumeSchema])
def list_candidates(
    recruiter_uuid: Optional[str] = Query(None, description="Filter by recruiter UUID"),
    batch_tag: Optional[str] = Query(None, description="Filter by batch tag"),
    skill: Optional[str] = Query(None, description="Filter by skill (array_contains)"),
    name: Optional[str] = Query(None, description="Prefix search on name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=200, description="Page size")
):
    db = _init_firestore_client()
    try:
        collection = db.collection(CANDIDATE_COLLECTION)
        query = collection

        if recruiter_uuid:
            query = query.where("recruiter_uuid", "==", recruiter_uuid)
        if batch_tag:
            query = query.where("batch_tag", "==", batch_tag)
        if skill:
            query = query.where("skills", "array_contains", skill)
        if name:
            prefix = name
            upper = prefix + u"\uf8ff"
            query = query.where("name", ">=", prefix).where("name", "<=", upper)

        offset_val = (page - 1) * page_size
        docs = query.offset(offset_val).limit(page_size).stream()

        results = []
        for doc in docs:
            results.append(doc_to_resume(doc))

        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error querying Firestore: %s", e)
        raise HTTPException(status_code=500, detail=f"Error querying Firestore: {e}")


@router.get("/candidates/{candidate_id}", response_model=ResumeSchema)
def get_candidate(candidate_id: str):
    db = _init_firestore_client()
    try:
        doc_ref = db.collection(CANDIDATE_COLLECTION).document(candidate_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return ResumeSchema.parse_obj(doc_to_resume(doc))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching candidate: %s", e)
        raise HTTPException(status_code=500, detail=f"Error fetching candidate: {e}")


@router.get("/candidates/{candidate_id}/raw")
def get_candidate_raw(candidate_id: str):
    db = _init_firestore_client()
    try:
        doc = db.collection(CANDIDATE_COLLECTION).document(candidate_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return doc.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching candidate raw doc: %s", e)
        raise HTTPException(status_code=500, detail=f"Error fetching candidate raw doc: {e}")