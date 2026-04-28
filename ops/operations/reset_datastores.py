"""
Purpose: Reset the Qdrant collection and PostgreSQL documents table for a clean run.

This script:
1. Deletes the 'documents' collection from the Qdrant vector database.
2. Re-creates the 'documents' collection with the correct configuration.
3. Truncates the 'documents' table in the PostgreSQL database.

WARNING: This script is destructive and will delete data.

Dependencies:
- qdrant-client
- psycopg
- python-dotenv

Usage:
  python ops/operations/reset_datastores.py

Configuration: Set POSTGRES_* and QDRANT_* env vars; defaults are for local dev only.
"""

import asyncio
import os

import psycopg
from qdrant_client import QdrantClient, models

# --- Qdrant Configuration ---
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "documents"
VECTOR_SIZE = 384  # From docker-compose all-minilm-l6-v2

# --- PostgreSQL Configuration (use env vars in production) ---
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5532"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "aio")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")


def reset_qdrant_collection():
    """Deletes and recreates the Qdrant collection."""
    print("Connecting to Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"Connection to Qdrant at {QDRANT_HOST}:{QDRANT_PORT} successful.")

    try:
        print(f"Checking for collection '{COLLECTION_NAME}'...")
        collections_response = client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]

        if COLLECTION_NAME in existing_collections:
            print(f"Collection '{COLLECTION_NAME}' exists. Deleting...")
            client.delete_collection(collection_name=COLLECTION_NAME)
            print(f"Collection '{COLLECTION_NAME}' deleted successfully.")
        else:
            print(f"Collection '{COLLECTION_NAME}' does not exist. No need to delete.")

        print(f"Re-creating collection '{COLLECTION_NAME}'...")
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
        print(f"Collection '{COLLECTION_NAME}' re-created successfully.")

    except Exception as e:
        print(f"An error occurred during Qdrant reset: {e}")
        raise


async def reset_postgres_documents_table():
    """Truncates the documents table in PostgreSQL."""
    try:
        print("Connecting to PostgreSQL...")
        conn_str = f"dbname='{POSTGRES_DB}' user='{POSTGRES_USER}' password='{POSTGRES_PASSWORD}' host='{POSTGRES_HOST}' port='{POSTGRES_PORT}'"
        async with await psycopg.AsyncConnection.connect(conn_str) as aconn:
            print(f"Connection to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT} successful.")

            async with aconn.cursor() as cur:
                table_to_truncate = "documents"
                print(f"Truncating table '{table_to_truncate}'...")
                await cur.execute(f"TRUNCATE TABLE {table_to_truncate} RESTART IDENTITY CASCADE;")
                await aconn.commit()
                print(f"Table '{table_to_truncate}' truncated successfully.")

    except Exception as e:
        print(f"An error occurred during PostgreSQL reset: {e}")
        raise


async def main():
    print("--- Starting Data Store Reset ---")
    try:
        reset_qdrant_collection()
        print("\n" + "-" * 20 + "\n")
        await reset_postgres_documents_table()
        print("\n--- Data Store Reset Completed Successfully ---")
    except Exception as e:
        print(f"\n--- Data Store Reset Failed: {e} ---")


if __name__ == "__main__":
    asyncio.run(main())
