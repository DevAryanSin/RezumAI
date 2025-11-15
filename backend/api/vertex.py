"""
vertex.py

This script performs semantic search for candidates using Google Cloud Vertex AI.

It takes a user query, generates a text embedding for it, and then queries a
Vertex AI Vector Search (Matching Engine) index to find the most similar
candidates stored in the vector database.

Required Packages:
pip install google-cloud-aiplatform

Authentication:
This script assumes you have a service account JSON key.
Set the GOOGLE_APPLICATION_CREDENTIALS environment variable *before*
running this script:

export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
"""

import os
import sys
from typing import List, Dict, Any
from google.api_core import exceptions

try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (
        MatchingEngineIndexEndpoint,
    )
    from vertexai.language_models import TextEmbeddingModel
except ImportError:
    print("Error: 'google-cloud-aiplatform' library not found.")
    print("Please install it: pip install google-cloud-aiplatform")
    sys.exit(1)

# --- CONFIGURATION: UPDATE THESE VALUES ---

# Your Google Cloud project ID
PROJECT_ID = "rezumai-478204"

# The region where your Vertex AI resources are located (e.g., "us-central1")
REGION = "us-central1"

# The embedding model you used to create the vectors for your candidates.
# Ensure this MATCHES the model used to populate your index.
EMBEDDING_MODEL_NAME = "text-embedding-004"

# The ID of your Vertex AI Vector Search Index Endpoint
# Find this in the Vertex AI -> Vector Search -> Index Endpoints section
INDEX_ENDPOINT_ID = "9074104537291161600"

# The ID of the specific index deployed to the endpoint
# Find this on the details page of your Index Endpoint
DEPLOYED_INDEX_ID = "resume_index_v1_1763142505680"

# --- END CONFIGURATION ---


def initialize_vertex_ai():
    """Initializes the Vertex AI SDK with project and location."""
    try:
        aiplatform.init(project=PROJECT_ID, location=REGION)
        print(f"Vertex AI initialized for project '{PROJECT_ID}' in region '{REGION}'.")
    except Exception as e:
        print(f"Error initializing Vertex AI. Have you authenticated?")
        print(f"Details: {e}")
        sys.exit(1)


def get_text_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for a given text query.

    Args:
        text: The user's query string.

    Returns:
        A list of floats representing the vector embedding.
    """
    try:
        model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


def find_best_candidates(query: str, num_neighbors: int = 5) -> List[Dict[str, Any]]:
    """
    Finds the best candidate matches from Vector Search.

    Args:
        query: The user's search query (e.g., "React developer with 3 years experience").
        num_neighbors: The number of top candidates to return.

    Returns:
        A list of dictionaries, each containing a candidate 'id' and 'distance' (similarity).
    """
    print(f"\nSearching for {num_neighbors} best candidates for query: '{query}'")

    # 1. Generate embedding for the user's query
    query_embedding = get_text_embedding(query)
    if not query_embedding:
        print("Could not generate query embedding. Aborting search.")
        return []

    print(f"Successfully generated query embedding (dimension: {len(query_embedding)}).")

    try:
        # 2. Get a reference to the Matching Engine Index Endpoint
        index_endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=INDEX_ENDPOINT_ID,
            project=PROJECT_ID,
            location=REGION,
        )

        # 3. Perform the semantic search (find nearest neighbors)
        # The query_embedding must be wrapped in a list
        response = index_endpoint.find_neighbors(
            queries=[query_embedding],
            deployed_index_id=DEPLOYED_INDEX_ID,
            num_neighbors=num_neighbors,
        )

        print("Search successful.")

        # 4. Process and return the results
        results = []
        if response and response[0]:
            for neighbor in response[0]:
                # neighbor.id is the 'datapoint_id' you specified when
                # uploading the vectors. This is your candidate's unique ID.
                results.append(
                    {
                        "id": neighbor.id,
                        "distance": neighbor.distance,
                    }
                )
        return results

    except exceptions.NotFound:
        print(f"Error: Could not find Index Endpoint '{INDEX_ENDPOINT_ID}'")
        print("Please check your 'INDEX_ENDPOINT_ID' and 'REGION' configuration.")
        return []
    except exceptions.PermissionDenied:
        print("Error: Permission denied.")
        print("Please check your service account permissions and ensure")
        print("GOOGLE_APPLICATION_CREDENTIALS is set correctly.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during search: {e}")
        return []


# Main execution block to run the script
if __name__ == "__main__":
    # Check for service account authentication
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your service account key JSON file.")
        sys.exit(1)

    # Check for placeholder values
    if PROJECT_ID == "your-gcp-project-id" or INDEX_ENDPOINT_ID == "your-index-endpoint-id":
        print("Error: Please update the placeholder values in the 'CONFIGURATION' section.")
        sys.exit(1)

    # Initialize Vertex AI
    initialize_vertex_ai()

    # --- Example Usage ---
    user_query = "Senior software engineer with strong experience in Python, GCP, and machine learning"

    # Find the top 3 matching candidates
    best_candidates = find_best_candidates(user_query, num_neighbors=3)

    if best_candidates:
        print("\n--- Best Candidate Matches ---")
        for i, candidate in enumerate(best_candidates):
            print(f"  Rank {i+1}:")
            print(f"    Candidate ID: {candidate['id']}")
            print(f"    Match Score (Distance): {candidate['distance']:.4f}")
    else:
        print("\nNo candidates found for this query.")