# chatbot_search_integration.py
"""
Integration code for chatbot to use vector search.
Add this to your main.py or import as a separate module.
"""
from typing import List, Dict, Optional
from google.cloud import firestore
from . import vertex_search


def search_candidates(
    query: str = "",
    recruiter_uuid: str = "",
    batch_tag: str = "",
    top_k: int = 10,
    neighbor_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Search for candidates using vector search and return full profiles.

    Args:
        query: Search query (used as fallback if neighbor_ids is not provided)
        recruiter_uuid: UUID of the recruiter
        batch_tag: Batch tag for filtering
        top_k: Number of candidates to return
        neighbor_ids: Optional list of chunk/datapoint ids returned by vector search

    Returns:
        List of candidate profiles (dicts) with basic info
    """
    try:
        print(f"\n{'='*70}")
        print("CANDIDATE SEARCH")
        print(f"Query: {query}")
        print(f"Recruiter: {recruiter_uuid}")
        print(f"Batch: {batch_tag}")
        print(f"Top K: {top_k}")
        print(f"{'='*70}\n")

        # ensure vector search initialized
        try:
            vertex_search.initialize_globals()
        except Exception:
            # initialize_globals may already have been called by FastAPI lifespan
            pass

        # If neighbor_ids not passed, run a vector search to get chunk ids
        chunk_ids = []
        if neighbor_ids:
            chunk_ids = list(neighbor_ids)
            print(f"[Search] Using provided neighbor_ids ({len(chunk_ids)})")
        else:
            # get more chunks to map to unique candidates
            try:
                chunk_ids = vertex_search.find_neighbor_ids(
                    query=query,
                    batch_tag=batch_tag,
                    recruiter_uuid=recruiter_uuid,
                    top_k=top_k * 3
                ) or []
            except TypeError:
                # older signature without recruiter_uuid
                chunk_ids = vertex_search.find_neighbor_ids(
                    query=query,
                    batch_tag=batch_tag,
                    top_k=top_k * 3
                ) or []
            except Exception as e:
                print(f"[Search] Error calling vector search: {e}")
                chunk_ids = []

        print(f"[Search] Step 1: Found {len(chunk_ids)} matching chunks")
        if chunk_ids:
            print(f"[Search] Sample chunks: {chunk_ids[:5]}")

        if not chunk_ids:
            print("[Search] ✗ No chunks found for query")
            return []

        # Step 3: Extract unique candidate IDs from chunk ids using helper in vertex_search
        try:
            candidate_ids = vertex_search.extract_candidate_ids(chunk_ids)
        except Exception:
            # fallback: assume chunk id format candidateid_suffix and attempt to extract prefix
            candidate_ids = []
            for cid in chunk_ids:
                # e.g., cnd_123_summary -> cnd_123
                if "_" in cid:
                    parts = cid.split("_")
                    # naive heuristic: first two parts as id if starts with cnd
                    if parts[0].startswith("cnd") and len(parts) >= 2:
                        candidate_ids.append("_".join(parts[:2]))
                    else:
                        candidate_ids.append(parts[0])
                else:
                    candidate_ids.append(cid)
            # dedupe
            candidate_ids = list(dict.fromkeys(candidate_ids))

        print(f"[Search] Step 2: Extracted {len(candidate_ids)} unique candidate IDs")

        if not candidate_ids:
            print("[Search] ✗ No candidate IDs extracted from chunks")
            return []

        # Step 4: Fetch candidate profiles from Firestore
        db = firestore.Client()
        candidates = []

        print("[Search] Step 3: Fetching profiles from Firestore...")
        for i, candidate_id in enumerate(candidate_ids[:top_k]):
            try:
                doc = db.collection("candidates").document(candidate_id).get()

                if not doc.exists:
                    print(f"[Search]   {i+1}. {candidate_id} - NOT FOUND in Firestore")
                    continue

                data = doc.to_dict() or {}

                # Verify filters match (double-check)
                if batch_tag and data.get("batch_tag") != batch_tag:
                    print(f"[Search]   {i+1}. {candidate_id} - SKIPPED (batch_tag mismatch)")
                    continue

                if recruiter_uuid and data.get("recruiter_uuid") != recruiter_uuid:
                    print(f"[Search]   {i+1}. {candidate_id} - SKIPPED (recruiter mismatch)")
                    continue

                # Normalize and append
                candidates.append(data)
                print(f"[Search]   {i+1}. {candidate_id} - ✓ {data.get('name', 'Unknown')}")

            except Exception as e:
                print(f"[Search]   {i+1}. {candidate_id} - ERROR: {e}")
                continue

        print(f"\n[Search] ✓ Step 4: Returning {len(candidates)} candidates")
        print(f"{'='*70}\n")

        return candidates

    except Exception as e:
        print(f"\n[Search] ✗ ERROR in search_candidates: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_candidate_for_chat(candidate: Dict) -> Dict:
    """
    Format a candidate profile for display / prompt building in chat.

    Returns a dict with predictable keys (name, summary, skills, experience, education).
    """
    name = candidate.get("name") or candidate.get("candidate_name") or candidate.get("candidateId") or "Unknown"
    summary = candidate.get("summary") or candidate.get("profile_summary") or ""
    skills = candidate.get("skills") or []
    work_experience = candidate.get("work_experience") or []
    education = candidate.get("education") or []

    # create a short textual summary as well as structured fields
    short_summary = summary.strip()
    if not short_summary:
        # try to build short summary from role / skills if missing
        top_skills = ", ".join(skills[:5]) if skills else ""
        top_role = ""
        if isinstance(work_experience, list) and len(work_experience) > 0:
            top_role = work_experience[0].get("title", "")
        short_summary = " ".join(p for p in [top_role, top_skills] if p).strip()

    return {
        "name": name,
        "summary": short_summary,
        "skills": skills,
        "work_experience": work_experience,
        "education": education,
        # keep original payload for reference
        "_raw": candidate
    }


# ============================================================
# Example chat handler usage (call this from your FastAPI route)
# ============================================================
def chat_handler_example(query: str, recruiter_uuid: str, batch_tag: str, top_k: int = 5):
    """
    Example of how to integrate search into your chat endpoint.
    Replaces the earlier broken example that referenced `request`.
    """
    # Search for candidates
    candidates = search_candidates(
        query=query,
        recruiter_uuid=recruiter_uuid,
        batch_tag=batch_tag,
        top_k=top_k
    )

    if not candidates:
        return {
            "response": "I couldn't find any candidates matching your query. Try:\n"
                        "- Using different keywords\n"
                        "- Being less specific\n"
                        "- Checking if candidates were uploaded to this batch",
            "candidates": []
        }

    # Format top candidates
    formatted_list = [format_candidate_for_chat(c) for c in candidates[:10]]

    response_text = f"I found {len(formatted_list)} candidates matching your query:\n\n"
    for i, cand in enumerate(formatted_list[:5], 1):
        # build a small readable block
        response_text += f"{i}. {cand['name']}\n"
        if cand['summary']:
            response_text += f"   Summary: {cand['summary']}\n"
        if cand['skills']:
            response_text += f"   Skills: {', '.join(cand['skills'][:8])}\n"
        response_text += "-" * 40 + "\n"

    if len(formatted_list) > 5:
        response_text += f"\n... and {len(formatted_list) - 5} more candidates."

    return {
        "response": response_text,
        "candidates": formatted_list
    }


# ============================================================
# Debugging / Testing Functions
# ============================================================
def debug_search(batch_tag: str, recruiter_uuid: Optional[str] = None):
    """
    Debug function to test search without a specific query.
    Useful for verifying data is indexed correctly.
    """
    print(f"\n{'='*70}")
    print("DEBUG SEARCH")
    print(f"{'='*70}\n")

    # Test 1: Search with generic query
    print("Test 1: Generic query search")
    results = search_candidates(
        query="software engineer",
        recruiter_uuid=recruiter_uuid or "test",
        batch_tag=batch_tag,
        top_k=5
    )
    print(f"Results: {len(results)} candidates\n")

    # Test 2: List all candidates in batch (from Firestore)
    print("Test 2: All candidates in Firestore for this batch")
    db = firestore.Client()
    docs = db.collection("candidates").where("batch_tag", "==", batch_tag).stream()

    firestore_candidates = []
    for doc in docs:
        data = doc.to_dict()
        firestore_candidates.append(data)
        print(f"  - {data.get('candidate_id')}: {data.get('name')}")

    print(f"\nTotal in Firestore: {len(firestore_candidates)}")
    print(f"Total in search results: {len(results)}")

    if len(firestore_candidates) > 0 and len(results) == 0:
        print("\n⚠️  WARNING: Candidates exist in Firestore but not in search results!")
        print("   This suggests vector indexing may have failed or is incomplete.")

    return results, firestore_candidates


def verify_vector_index_data(candidate_id: str):
    """
    Verify that a specific candidate's data was indexed in vector search.
    """
    from google.cloud import firestore

    print(f"\n{'='*70}")
    print(f"VERIFY CANDIDATE: {candidate_id}")
    print(f"{'='*70}\n")

    # Get candidate from Firestore
    db = firestore.Client()
    doc = db.collection("candidates").document(candidate_id).get()

    if not doc.exists:
        print(f"✗ Candidate {candidate_id} not found in Firestore")
        return False

    data = doc.to_dict()
    print(f"✓ Found in Firestore:")
    print(f"  Name: {data.get('name')}")
    print(f"  Batch: {data.get('batch_tag')}")
    print(f"  Recruiter: {data.get('recruiter_uuid')}")

    # Try searching for unique terms from this candidate
    test_queries = [
        data.get('name', ''),
        " ".join(data.get('skills', [])[:3]),
        data.get('summary', '')[:50]
    ]

    print(f"\n✓ Testing search with candidate's data:")
    for i, q in enumerate(test_queries, 1):
        if not q:
            continue

        print(f"\n  Test {i}: '{q[:50]}...'")

        try:
            vertex_search.initialize_globals()
            chunk_ids = vertex_search.find_neighbor_ids(
                query=q,
                batch_tag=data.get('batch_tag'),
                recruiter_uuid=data.get('recruiter_uuid'),
                top_k=10
            )

            found = any(candidate_id in cid for cid in chunk_ids)

            if found:
                print("    ✓ FOUND in search results")
                return True
            else:
                print(f"    ✗ NOT FOUND (got {len(chunk_ids)} other results)")

        except Exception as e:
            print(f"    ✗ ERROR: {e}")

    print("\n✗ Candidate NOT found in any vector search test")
    print("   This suggests the candidate was not indexed properly.")
    return False


if __name__ == "__main__":
    # Test the search from CLI:
    import sys

    if len(sys.argv) > 2:
        batch_tag = sys.argv[1]
        recruiter_uuid = sys.argv[2] if len(sys.argv) > 2 else None
        debug_search(batch_tag, recruiter_uuid)
    else:
        print("Usage: python chatbot_search_integration.py <batch_tag> <recruiter_uuid>")
