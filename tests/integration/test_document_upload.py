#!/usr/bin/env python3
"""
Test document upload to verify Qdrant point ID fix.

This script tests document upload and processing via the corpus service
to ensure the Qdrant point ID issue is resolved.

Usage:
pytest tests/integration/test_document_upload.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

import aiohttp
from jose import jwt


class DocumentUploadTester:
    def __init__(self):
        self.base_url = "http://localhost:8003"  # Corpus service port
        # Use JWT_SECRET from env (e.g. config/env/env.test) or test placeholder
        self.jwt_secret = os.environ.get("JWT_SECRET", "test_jwt_secret_min_32_chars_for_hs256")
        self.jwt_algorithm = "HS256"
        self.jwt_issuer = "ai-operations-platform"

    def generate_valid_jwt(self) -> str:
        """Generate a valid JWT token using the service's secret."""
        payload = {
            "sub": "test-user",
            "user_id": str(uuid.uuid4()),  # Use proper UUID format
            "role": "user",
            "token_type": "access",
            "iss": self.jwt_issuer,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def test_document_upload(self, session: aiohttp.ClientSession):
        """Test document upload and processing."""
        print("🔍 Testing document upload and processing...")

        token = self.generate_valid_jwt()

        # Create a simple test document
        test_content = "This is a test document for checking if Qdrant point ID issues are resolved. It contains some sample text that should be chunked and processed for embeddings."

        # Create form data
        data = aiohttp.FormData()
        data.add_field("title", "Test Document for Qdrant Fix")
        data.add_field("source", "integration-test")
        data.add_field("author", "test-system")
        data.add_field("classification", "unclassified")
        data.add_field("tags", "test,qdrant-fix")
        data.add_field("embedding_model", "all-minilm-l6-v2")
        data.add_field("process_async", "false")  # Process synchronously for immediate results
        data.add_field(
            "file", test_content.encode(), filename="test_document.txt", content_type="text/plain"
        )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with session.post(
                f"{self.base_url}/api/v1/documents/", data=data, headers=headers
            ) as response:
                status = response.status
                if status == 202:  # Accepted for processing
                    response_data = await response.json()
                    print(f"   ✅ Status: {status}")
                    print(f"   Document ID: {response_data.get('document_id', 'N/A')}")
                    print(f"   Status: {response_data.get('status', 'N/A')}")
                    print(f"   Message: {response_data.get('message', 'N/A')}")
                    return True, response_data.get("document_id")
                await response.text()
                print(f"   ❌ Status: {status}")
                return False, None
        except Exception as e:
            print(f"   ❌ Request failed: {type(e).__name__}")
            return False, None

    async def test_document_status(self, session: aiohttp.ClientSession, document_id: str):
        """Check document processing status."""
        print(f"🔍 Checking processing status for document {document_id}...")

        token = self.generate_valid_jwt()

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with session.get(
                f"{self.base_url}/api/v1/documents/{document_id}/status", headers=headers
            ) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {status}")
                    print(f"   Processing status: {data.get('status', 'N/A')}")
                    if data.get("error_message"):
                        print("   Error: [present]")
                        return False
                    print(f"   Chunks: {data.get('num_chunks', 'N/A')}")
                    print(f"   Model: {data.get('embedding_model', 'N/A')}")
                    return data.get("status") == "completed"
                await response.text()
                print(f"   ❌ Status: {status}")
                return False
        except Exception as e:
            print(f"   ❌ Request failed: {type(e).__name__}")
            return False

    async def run_test(self):
        """Run the document upload test."""
        print("🚀 Testing Document Upload and Qdrant Processing")
        print("=" * 60)

        async with aiohttp.ClientSession() as session:
            # Test document upload
            upload_success, document_id = await self.test_document_upload(session)
            print()

            if not upload_success or not document_id:
                print("❌ Document upload failed")
                return False

            # Wait a moment for processing
            await asyncio.sleep(2)

            # Check processing status
            status_success = await self.test_document_status(session, document_id)
            print()

            if status_success:
                print("🎉 Document upload and processing completed successfully!")
                print("💡 Qdrant point ID issue appears to be resolved!")
                return True
            print("❌ Document processing failed - check logs for Qdrant errors")
            return False


async def main():
    """Main test function."""
    tester = DocumentUploadTester()
    success = await tester.run_test()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Document Upload with Qdrant Point ID Fix")
    print("Make sure the corpus service is running on localhost:8003")
    print("And the embedding service is running on localhost:8002")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}")
        sys.exit(1)
