import os
import sys
import time
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ops.demonstrate_enhanced_pipeline_fixed import (
    AIOPEnhancedPipelineClient,
    display_response,
)


def main():
    """
    A simple script to test the document deletion process and its effect on usage_stats.
    """
    print("--- Starting Deletion Process Test ---")

    api_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    username = os.environ.get("API_USERNAME", "testuser")
    password = os.environ.get("API_PASSWORD", "password")

    client = AIOPEnhancedPipelineClient(api_url, username, password)

    if not client.authenticate():
        print("Authentication failed. Exiting.")
        sys.exit(1)

    # 1. Ingest a single document
    doc_to_ingest = {
        "file_path": "corpus_docs/nist.cswp.29.pdf",
        "title": "Test Deletion Document",
        "source": "Test Suite",
        "author": "Cline",
        "classification": "public",
        "tags": ["testing", "deletion"],
        "metadata": {"test_id": str(uuid.uuid4())},
    }

    print("\n--- Step 1: Ingesting Document ---")
    ingest_response = client.ingest_document(doc_to_ingest)
    display_response("Ingest Response", ingest_response)

    if "document_id" not in ingest_response:
        print("Failed to ingest document. Aborting test.")
        sys.exit(1)

    document_id = ingest_response["document_id"]
    client.get_document_when_ready(document_id)
    print(f"Document {document_id} ingested successfully.")

    # 2. Perform a search to create a usage_stats entry
    print("\n--- Step 2: Performing Search to Generate Usage Stats ---")
    search_query = "NIST Cybersecurity Framework"
    search_results = client.search_documents(search_query, limit=1)
    display_response(f"Search Results for '{search_query}'", search_results)

    # Give a moment for the stats to be written
    time.sleep(2)

    # 3. Delete the document
    print(f"\n--- Step 3: Deleting Document {document_id} ---")
    delete_response = client.delete_document(document_id)
    display_response(f"Deletion Response for Document ID: {document_id}", delete_response)

    print("\n--- Deletion Process Test Complete ---")
    print("Please check the database to verify the usage_stats table.")


if __name__ == "__main__":
    main()
