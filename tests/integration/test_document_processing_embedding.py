#!/usr/bin/env python3
"""
Test the exact embedding request that happens during document processing.

This script simulates the exact embedding request that the ingestion service
makes during document processing to identify the 422 validation issue.

Usage:
pytest tests/integration/test_document_processing_embedding.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

import aiohttp
from jose import jwt


async def test_document_processing_embedding():
    """Test the exact embedding request used during document processing."""
    print("🔍 Testing Document Processing Embedding Request")
    print("=" * 60)

    # Use JWT_SECRET from env (e.g. config/env/env.test) or test placeholder
    jwt_secret = os.environ.get("JWT_SECRET", "test_jwt_secret_min_32_chars_for_hs256")
    jwt_algorithm = "HS256"
    jwt_issuer = "ai-operations-platform"

    payload = {
        "sub": "test-user",
        "user_id": str(uuid.uuid4()),
        "role": "user",
        "token_type": "access",
        "iss": jwt_issuer,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

    # Test chunks like those from document processing
    test_chunks = [
        "This is a test document for checking if Qdrant point ID issues are resolved.",
        "It contains some sample text that should be chunked and processed for embeddings.",
        "Each chunk represents a piece of text that would be extracted from a document.",
    ]

    # Test different model parameters that might be used during document processing
    test_cases = [
        {"model": "local", "description": "Using 'local' model type"},
        {"model": "all-minilm-l6-v2", "description": "Using specific model name"},
        {"model": None, "description": "Using no model (default)"},
    ]

    embedding_url = "http://localhost:8002/v1/embeddings"

    async with aiohttp.ClientSession() as session:
        for i, case in enumerate(test_cases, 1):
            print(f"\n🔍 Test Case {i}: {case['description']}")

            # Create request payload
            payload_data = {"input": test_chunks, "encoding_format": "float"}

            # Add model if specified
            if case["model"] is not None:
                payload_data["model"] = case["model"]

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

            print(f"   Request URL: {embedding_url}")
            print(f"   Model: {case['model']}")
            print(f"   Chunks: {len(test_chunks)}")

            try:
                async with session.post(
                    embedding_url, json=payload_data, headers=headers
                ) as response:
                    status = response.status

                    if status == 200:
                        data = await response.json()
                        print(f"   ✅ Status: {status}")
                        print(f"   Embeddings received: {len(data.get('data', []))}")
                        print(f"   Model used: {data.get('model', 'N/A')}")

                        if data.get("data"):
                            first_embedding = data["data"][0].get("embedding", [])
                            print(f"   Embedding dimensions: {len(first_embedding)}")
                    else:
                        await response.text()
                        print(f"   ❌ Status: {status}")

            except Exception as e:
                print(f"   ❌ Request failed: {type(e).__name__}")


async def main():
    """Main test function."""
    try:
        await test_document_processing_embedding()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Document Processing Embedding Requests")
    print("Make sure the embedding service is running on localhost:8002")
    print()

    asyncio.run(main())
