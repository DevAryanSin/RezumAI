import os
from typing import List, Dict, Any
import math
from time import perf_counter

from google.cloud import firestore
import vertexai
from vertexai.language_models import TextEmbeddingModel

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("VERTEX_LOCATION", os.getenv("LOCATION", "us-central1"))
EMBED_MODEL = os.getenv("VERTEX_EMBED_MODEL", "text-embedding-004")

_firestore = None
_embed_model = None


def _init_clients():
    global _firestore, _embed_model
    if _firestore is None:
        _firestore = firestore.Client(project=PROJECT_ID)
    if _embed_model is None:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        _embed_model = TextEmbeddingModel.from_pretrained(EMBED_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    _init_clients()
    start = perf_counter()
    result = _embed_model.get_embeddings(texts)
    vectors: List[List[float]] = []
    for r in result:
        # API returns objects with .values iterable
        vectors.append(list(r.values))
    dur = (perf_counter() - start) * 1000
    print(f"[embeddings] embedded {len(texts)} chunks in {dur:.1f} ms")
    return vectors


def upsert_chunks_firestore(batch_id: str, candidate_id: str, chunks: List[str], vectors: List[List[float]]) -> None:
    _init_clients()
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must be same length")
    batch = _firestore.batch()
    col = _firestore.collection("resume_chunks")
    for i, (txt, vec) in enumerate(zip(chunks, vectors)):
        doc_id = f"{batch_id}__{candidate_id}__{i}"
        ref = col.document(doc_id)
        batch.set(ref, {
            "batch_id": batch_id,
            "candidate_id": candidate_id,
            "chunk_id": i,
            "text": txt,
            "vector": vec,
        })
    batch.commit()
    print(f"[firestore] Stored {len(chunks)} chunks for batch_id={batch_id}, candidate_id={candidate_id}")


def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def knn_search_firestore(batch_id: str, query_vec: List[float], top_k: int = 10, filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    _init_clients()
    print(f"[search] Searching for batch_id: {batch_id}")
    
    # Filter by batch_id in Firestore; additional filters can be applied post-fetch
    q = _firestore.collection("resume_chunks").where("batch_id", "==", batch_id).stream()
    scored: List[Dict[str, Any]] = []
    doc_count = 0
    
    for doc in q:
        doc_count += 1
        d = doc.to_dict()
        if filters:
            # optional simple filters on text
            if (comp := filters.get("company")):
                if comp.lower() not in (d.get("text") or "").lower():
                    continue
            # years_experience: naive filter
            if (yrs := filters.get("years_experience")):
                # pass-through; real impl would parse dates; keeping minimal
                pass
        sim = cosine_sim(query_vec, d.get("vector", []))
        d["_score"] = sim
        scored.append(d)
    
    print(f"[search] Found {doc_count} documents for batch_id={batch_id}, returning top {min(top_k, len(scored))}")
    scored.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
    return scored[:top_k]
