"""
Robust Vector Search module for Vertex AI Matching Engine.
Handles multiple SDK versions and provides fallback mechanisms.
"""
import os
import json
from typing import List, Optional, Dict, Any
import requests

import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
import google.cloud.aiplatform as aiplatform
from google.auth import default
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account

# -------------------------------------------------------------------
# ENV
# -------------------------------------------------------------------
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
MODEL_LOCATION = os.getenv("MODEL_LOCATION", LOCATION)
INDEX_ID = os.getenv("INDEX_ID")
ENDPOINT_ID = os.getenv("ENDPOINT_ID") or os.getenv("INDEX_ENDPOINT_ID")

if not ENDPOINT_ID:
    raise ValueError("ENDPOINT_ID (or INDEX_ENDPOINT_ID) must be set.")
if not INDEX_ID:
    raise ValueError("INDEX_ID must be set.")
if not PROJECT_ID:
    raise ValueError("PROJECT_ID must be set.")

INDEX_ENDPOINT_FULL_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{ENDPOINT_ID}"
INDEX_FULL_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexes/{INDEX_ID}"

# Globals
matching_engine_endpoint: Optional[aiplatform.MatchingEngineIndexEndpoint] = None
DEPLOYMENT_ID: Optional[str] = None
embedding_model: Optional[TextEmbeddingModel] = None
gen_model: Optional[GenerativeModel] = None
_credentials = None


# -------------------------------------------------------------------
# INIT
# -------------------------------------------------------------------
def initialize_globals() -> None:
    """Initialize all global resources needed for vector search."""
    global matching_engine_endpoint, embedding_model, gen_model, DEPLOYMENT_ID, _credentials

    if matching_engine_endpoint is not None and embedding_model is not None:
        print("[Init] Globals already initialized.")
        return

    print("[Init] Initializing Vertex AI components...")

    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)
    aiplatform.init(project=PROJECT_ID, location=LOCATION)

    # Load embedding model
    embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    print("[Init] ✓ Embedding model loaded: text-embedding-004")

    # Load generative model
    gen_model = GenerativeModel("gemini-2.0-flash-001")
    print("[Init] ✓ Generative model loaded: gemini-2.0-flash-001")

    # Get credentials for REST API fallback
    try:
        _credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        print("[Init] ✓ Loaded default credentials")
    except Exception as e:
        print(f"[Init] Warning: Could not load default credentials: {e}")
        _credentials = None

    # Create matching engine endpoint wrapper
    try:
        matching_engine_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=INDEX_ENDPOINT_FULL_NAME
        )
        print(f"[Init] ✓ Created MatchingEngineIndexEndpoint: {ENDPOINT_ID}")
    except Exception as e:
        print(f"[Init] ✗ Failed to create MatchingEngineIndexEndpoint: {e}")
        raise

    # Discover deployed index ID
    DEPLOYMENT_ID = _discover_deployment_id()
    if not DEPLOYMENT_ID:
        raise RuntimeError(f"Could not find deployed index '{INDEX_ID}' on endpoint '{ENDPOINT_ID}'")
    
    print(f"[Init] ✓ Using deployed index ID: {DEPLOYMENT_ID}")
    print("[Init] ✓ Initialization complete!")


def _discover_deployment_id() -> Optional[str]:
    """Discover the deployed index ID from the endpoint."""
    try:
        # Try using the endpoint's resource
        endpoint_resource = matching_engine_endpoint.gca_resource
        deployed_indexes = endpoint_resource.deployed_indexes
        
        print(f"[Init] Found {len(deployed_indexes)} deployed indexes")
        
        for di in deployed_indexes:
            di_index = di.index
            di_id = di.id
            
            print(f"[Init]   Checking: id={di_id}, index={di_index}")
            
            # Check if this is our index
            if di_index == INDEX_FULL_NAME or di_index.endswith(f"/{INDEX_ID}"):
                print(f"[Init]   ✓ Match found!")
                return di_id
        
        # If no exact match, use the first deployed index
        if deployed_indexes:
            fallback_id = deployed_indexes[0].id
            print(f"[Init]   Using first deployed index as fallback: {fallback_id}")
            return fallback_id
            
    except Exception as e:
        print(f"[Init] Error discovering deployment ID: {e}")
    
    return None


# -------------------------------------------------------------------
# SHUTDOWN
# -------------------------------------------------------------------
def shutdown_globals() -> None:
    """Reset all global resources."""
    global matching_engine_endpoint, DEPLOYMENT_ID, embedding_model, gen_model, _credentials
    matching_engine_endpoint = None
    DEPLOYMENT_ID = None
    embedding_model = None
    gen_model = None
    _credentials = None
    print("[Shutdown] Globals reset.")


# -------------------------------------------------------------------
# EMBEDDING
# -------------------------------------------------------------------
def get_text_embedding(text: str) -> List[float]:
    """Get text embedding using Vertex AI text-embedding-004 model."""
    if embedding_model is None:
        raise RuntimeError("Embedding model not initialized. Call initialize_globals() first.")
    
    try:
        embeddings = embedding_model.get_embeddings([text])
        return list(embeddings[0].values)
    except Exception as e:
        print(f"[Embedding] Error getting embedding: {e}")
        raise


# -------------------------------------------------------------------
# VECTOR SEARCH - Primary Method
# -------------------------------------------------------------------
def find_neighbor_ids(
    query: str,
    batch_tag: Optional[str] = None,
    recruiter_uuid: Optional[str] = None,
    top_k: int = 15
) -> List[str]:
    """
    Perform vector search to find similar candidates.
    
    Args:
        query: Search query text
        batch_tag: Optional batch tag for filtering
        recruiter_uuid: Optional recruiter UUID for filtering
        top_k: Number of results to return
        
    Returns:
        List of chunk IDs (datapoint IDs) from vector search
    """
    global matching_engine_endpoint, DEPLOYMENT_ID

    if matching_engine_endpoint is None or DEPLOYMENT_ID is None:
        raise RuntimeError("Vector search not initialized. Call initialize_globals() first.")

    print(f"\n{'='*60}")
    print(f"[Search] Starting vector search")
    print(f"[Search] Query: '{query[:80]}...'")
    print(f"[Search] Filters: batch_tag={batch_tag}, recruiter={recruiter_uuid}")
    print(f"[Search] Top K: {top_k}")
    print(f"{'='*60}\n")

    # Step 1: Get embedding
    try:
        embedding = get_text_embedding(query)
        print(f"[Search] ✓ Generated embedding ({len(embedding)} dimensions)")
    except Exception as e:
        print(f"[Search] ✗ Failed to generate embedding: {e}")
        raise

    # Step 2: Build filter restrictions
    filter_restrictions = []
    if batch_tag:
        filter_restrictions.append(
            aiplatform.matching_engine.matching_engine_index_endpoint.Namespace(
                name="batch_tag",
                allow_tokens=[batch_tag],
                deny_tokens=[]
            )
        )
    if recruiter_uuid:
        filter_restrictions.append(
            aiplatform.matching_engine.matching_engine_index_endpoint.Namespace(
                name="recruiter_uuid",
                allow_tokens=[recruiter_uuid],
                deny_tokens=[]
            )
        )
    
    if filter_restrictions:
        print(f"[Search] Built {len(filter_restrictions)} namespace filters")

    # Step 3: Try primary method - find_neighbors
    try:
        print(f"[Search] Method 1: Attempting find_neighbors()...")
        
        response = matching_engine_endpoint.find_neighbors(
            deployed_index_id=DEPLOYMENT_ID,
            queries=[embedding],
            num_neighbors=top_k
        )
        
        print(f"[Search] ✓ Method 1 succeeded")
        return _parse_find_neighbors_response(response, batch_tag, recruiter_uuid)
        
    except AttributeError as e:
        print(f"[Search] ✗ Method 1 failed (no find_neighbors method): {e}")
    except Exception as e:
        print(f"[Search] ✗ Method 1 failed: {e}")

    # Step 4: Try secondary method - match
    try:
        print(f"[Search] Method 2: Attempting match()...")
        
        # Build match parameters
        match_params = {
            "deployed_index_id": DEPLOYMENT_ID,
            "queries": [embedding],
            "num_neighbors": top_k
        }
        
        # Add filters if they exist
        if filter_restrictions:
            match_params["filter"] = filter_restrictions
        
        response = matching_engine_endpoint.match(**match_params)
        
        print(f"[Search] ✓ Method 2 succeeded")
        return _parse_match_response(response, batch_tag, recruiter_uuid)
        
    except Exception as e:
        print(f"[Search] ✗ Method 2 failed: {e}")

    # Step 5: Try REST API fallback
    try:
        print(f"[Search] Method 3: Attempting REST API...")
        
        response = _rest_api_search(
            embedding=embedding,
            batch_tag=batch_tag,
            recruiter_uuid=recruiter_uuid,
            top_k=top_k
        )
        
        print(f"[Search] ✓ Method 3 succeeded")
        return _parse_rest_response(response, batch_tag, recruiter_uuid)
        
    except Exception as e:
        print(f"[Search] ✗ Method 3 failed: {e}")
        import traceback
        traceback.print_exc()

    raise RuntimeError("All search methods failed. Check logs above for details.")


# -------------------------------------------------------------------
# Response Parsers
# -------------------------------------------------------------------
def _parse_find_neighbors_response(
    response: Any,
    batch_tag: Optional[str],
    recruiter_uuid: Optional[str]
) -> List[str]:
    """Parse response from find_neighbors() method."""
    try:
        print(f"[Parse] Parsing find_neighbors response...")
        
        # Response is list of lists of MatchNeighbor objects
        if not response or len(response) == 0:
            print(f"[Parse] Empty response")
            return []
        
        # Get first query's results
        neighbors = response[0] if len(response) > 0 else []
        print(f"[Parse] Found {len(neighbors)} neighbors")
        
        ids = []
        for i, neighbor in enumerate(neighbors):
            # MatchNeighbor has 'id' attribute
            nid = getattr(neighbor, 'id', None) or getattr(neighbor, 'datapoint_id', None)
            if nid:
                ids.append(str(nid))
                distance = getattr(neighbor, 'distance', 'N/A')
                if i < 5:  # Log first 5
                    print(f"[Parse]   {i+1}. ID: {nid}, Distance: {distance}")
        
        print(f"[Parse] ✓ Extracted {len(ids)} IDs")
        return ids
        
    except Exception as e:
        print(f"[Parse] ✗ Error parsing find_neighbors response: {e}")
        import traceback
        traceback.print_exc()
        return []


def _parse_match_response(
    response: Any,
    batch_tag: Optional[str],
    recruiter_uuid: Optional[str]
) -> List[str]:
    """Parse response from match() method."""
    try:
        print(f"[Parse] Parsing match response...")
        
        # Response is list of lists of MatchNeighbor objects
        if not response or len(response) == 0:
            print(f"[Parse] Empty response")
            return []
        
        # Get first query's results
        neighbors = response[0] if len(response) > 0 else []
        print(f"[Parse] Found {len(neighbors)} neighbors")
        
        ids = []
        for i, neighbor in enumerate(neighbors):
            nid = getattr(neighbor, 'id', None) or getattr(neighbor, 'datapoint_id', None)
            if nid:
                ids.append(str(nid))
                distance = getattr(neighbor, 'distance', 'N/A')
                if i < 5:  # Log first 5
                    print(f"[Parse]   {i+1}. ID: {nid}, Distance: {distance}")
        
        print(f"[Parse] ✓ Extracted {len(ids)} IDs")
        return ids
        
    except Exception as e:
        print(f"[Parse] ✗ Error parsing match response: {e}")
        import traceback
        traceback.print_exc()
        return []


def _parse_rest_response(
    response: Dict,
    batch_tag: Optional[str],
    recruiter_uuid: Optional[str]
) -> List[str]:
    """Parse response from REST API."""
    try:
        print(f"[Parse] Parsing REST response...")
        
        nearest = response.get("nearestNeighbors", [])
        if not nearest:
            print(f"[Parse] No nearestNeighbors in response")
            return []
        
        # Get first query's neighbors
        neighbors = nearest[0].get("neighbors", []) if len(nearest) > 0 else []
        print(f"[Parse] Found {len(neighbors)} neighbors")
        
        ids = []
        for i, n in enumerate(neighbors):
            nid = n.get("datapoint", {}).get("datapointId") or n.get("datapointId")
            if nid:
                ids.append(str(nid))
                distance = n.get("distance", "N/A")
                if i < 5:  # Log first 5
                    print(f"[Parse]   {i+1}. ID: {nid}, Distance: {distance}")
        
        print(f"[Parse] ✓ Extracted {len(ids)} IDs")
        return ids
        
    except Exception as e:
        print(f"[Parse] ✗ Error parsing REST response: {e}")
        import traceback
        traceback.print_exc()
        return []


# -------------------------------------------------------------------
# REST API Fallback
# -------------------------------------------------------------------
def _rest_api_search(
    embedding: List[float],
    batch_tag: Optional[str],
    recruiter_uuid: Optional[str],
    top_k: int
) -> Dict:
    """
    Fallback method: Use REST API directly.
    Uses online match endpoint for public endpoints.
    """
    if _credentials is None:
        raise RuntimeError("No credentials available for REST API")
    
    # Refresh credentials
    if not _credentials.valid:
        _credentials.refresh(AuthRequest())
    
    # Build URL - using the online match endpoint
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{INDEX_ENDPOINT_FULL_NAME}:readIndexDatapoints"
    
    headers = {
        "Authorization": f"Bearer {_credentials.token}",
        "Content-Type": "application/json"
    }
    
    # Build query
    query_payload = {
        "featureVector": embedding,
        "neighborCount": top_k
    }
    
    # Add restricts if provided
    if batch_tag or recruiter_uuid:
        restricts = []
        if batch_tag:
            restricts.append({
                "namespace": "batch_tag",
                "allowList": [batch_tag]
            })
        if recruiter_uuid:
            restricts.append({
                "namespace": "recruiter_uuid",
                "allowList": [recruiter_uuid]
            })
        query_payload["restricts"] = restricts
    
    body = {
        "deployedIndexId": DEPLOYMENT_ID,
        "queries": [query_payload]
    }
    
    print(f"[REST] POST {url}")
    print(f"[REST] Deployed Index: {DEPLOYMENT_ID}")
    print(f"[REST] Neighbor Count: {top_k}")
    
    response = requests.post(url, json=body, headers=headers, timeout=60)
    
    if response.status_code != 200:
        print(f"[REST] ✗ Error {response.status_code}: {response.text}")
        raise Exception(f"REST API error {response.status_code}: {response.text}")
    
    return response.json()


# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
def extract_candidate_ids(chunk_ids: List[str]) -> List[str]:
    """
    Extract unique candidate IDs from chunk IDs.
    
    Chunk ID format: candidateId_chunkType_index
    Example: cnd_123abc_summary, cnd_123abc_work_0
    
    Args:
        chunk_ids: List of chunk IDs from vector search
        
    Returns:
        List of unique candidate IDs
    """
    candidate_ids = set()
    
    for chunk_id in chunk_ids:
        parts = chunk_id.split('_')
        if len(parts) >= 2 and parts[0] == 'cnd':
            # Candidate ID is first two parts: cnd_uuid
            candidate_id = f"{parts[0]}_{parts[1]}"
            candidate_ids.add(candidate_id)
    
    result = list(candidate_ids)
    print(f"[Helper] Extracted {len(result)} unique candidates from {len(chunk_ids)} chunks")
    return result


def test_search(query: str = "python developer machine learning") -> bool:
    """
    Test function to verify vector search is working.
    
    Args:
        query: Test query string
        
    Returns:
        True if test passed, False otherwise
    """
    try:
        print(f"\n{'='*60}")
        print(f"VECTOR SEARCH TEST")
        print(f"{'='*60}")
        
        initialize_globals()
        
        results = find_neighbor_ids(query=query, top_k=5)
        
        if results:
            print(f"\n✓ TEST PASSED: Found {len(results)} results")
            return True
        else:
            print(f"\n✗ TEST FAILED: No results found")
            return False
            
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Run test if executed directly
    test_search()