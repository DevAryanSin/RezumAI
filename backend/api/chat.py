import os
import json
from time import perf_counter
from typing import Dict, Any, List, Tuple

import vertexai
from vertexai.generative_models import GenerativeModel

from .embeddings import embed_texts, knn_search_firestore

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("VERTEX_LOCATION", os.getenv("LOCATION", "us-central1"))
GEN_MODEL = os.getenv("VERTEX_GEN_MODEL", "gemini-1.5-flash")

_gen_model: GenerativeModel | None = None


def _init_gen() -> GenerativeModel:
    global _gen_model
    if _gen_model is None:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        _gen_model = GenerativeModel(GEN_MODEL)
    return _gen_model


async def extract_intent(query: str) -> Dict[str, Any]:
    model = _init_gen()
    sys_prompt = (
        "Extract structured filters from the recruiter's query as JSON with keys: "
        "company (string or null), years_experience (number or null). Only return JSON."
    )
    prompt = f"{sys_prompt}\nQuery: {query}"
    start = perf_counter()
    resp = model.generate_content(prompt)
    dur = (perf_counter() - start) * 1000
    print(f"[llm] intent latency {dur:.1f} ms")
    try:
        text = getattr(resp, "text", str(resp))
        data = json.loads(text)
        return {
            "company": data.get("company"),
            "years_experience": data.get("years_experience"),
        }
    except Exception:
        return {"company": None, "years_experience": None}


async def answer_query(batch_id: str, query: str) -> Dict[str, Any]:
    intent = await extract_intent(query)
    # embed query
    qvec = embed_texts([query])[0]
    # search KNN in Firestore with filters
    results = knn_search_firestore(batch_id, qvec, top_k=8, filters=intent)
    top_chunks = results[:5]

    # Build context
    pieces = []
    cand_scores: Dict[str, float] = {}
    for r in top_chunks:
        pieces.append(f"Candidate {r['candidate_id']} (score {r['_score']:.3f})\n{r['text']}")
        cand_scores[r['candidate_id']] = max(cand_scores.get(r['candidate_id'], 0.0), r['_score'])

    context = "\n\n---\n\n".join(pieces) if pieces else "No relevant chunks found."

    model = _init_gen()
    sys_prompt = (
        "You are an expert recruiting assistant. Use the provided chunks to answer. "
        "Return strict JSON with keys: answer (string), best_candidate_id (string or null)."
    )
    prompt = f"{sys_prompt}\n\nChunks:\n{context}\n\nRecruiter question: {query}\n\nJSON:"
    start = perf_counter()
    resp = model.generate_content(prompt)
    dur = (perf_counter() - start) * 1000
    print(f"[llm] answer latency {dur:.1f} ms")
    try:
        text = getattr(resp, "text", str(resp))
        data = json.loads(text)
    except Exception:
        # Fallback if model did not return JSON
        best = max(cand_scores.items(), key=lambda kv: kv[1])[0] if cand_scores else None
        data = {"answer": text if 'text' in locals() else "", "best_candidate_id": best}

    if not data.get("best_candidate_id"):
        best = max(cand_scores.items(), key=lambda kv: kv[1])[0] if cand_scores else None
        data["best_candidate_id"] = best

    return data
