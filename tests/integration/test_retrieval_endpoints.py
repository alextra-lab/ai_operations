#!/usr/bin/env python3
"""
Test the corpus service endpoints to verify 422 validation errors are resolved.

This script tests the actual endpoints that were failing with 422 errors.

Usage:
pytest tests/integration/test_retrieval_endpoints.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

import aiohttp
from jose import jwt


class RetrievalServiceTester:
    def __init__(self):
        self.base_url = "http://localhost:8003"  # Corpus service port
        # Use JWT_SECRET from env (e.g. config/env/env.test) or test placeholder
        self.jwt_secret = os.environ.get("JWT_SECRET", "test_jwt_secret_min_32_chars_for_hs256")
        self.jwt_algorithm = "HS256"
        self.jwt_issuer = "ai-operations-platform"

    def generate_valid_jwt(self) -> str:
        """Generate a valid JWT token using the service's secret."""
        import uuid

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

    async def test_health_endpoint(self, session: aiohttp.ClientSession):
        """Test the health endpoint."""
        print("🔍 Testing corpus service health endpoint...")
        try:
            async with session.get(f"{self.base_url}/health") as response:
                status = response.status
                await response.json()
                print(f"   Status: {status}")
                return status == 200
        except Exception as e:
            print(f"   ❌ Health check failed: {type(e).__name__}")
            return False

    async def test_semantic_search_endpoint(self, session: aiohttp.ClientSession):
        """Test the semantic search endpoint that calls embedding service."""
        print("🔍 Testing corpus service semantic search endpoint...")

        token = self.generate_valid_jwt()

        payload = {"query_text": "test search query", "top_k": 5}

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        try:
            async with session.post(
                f"{self.base_url}/api/v1/query/semantic-search", json=payload, headers=headers
            ) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {status}")
                    print(f"   Results count: {len(data.get('results', []))}")
                    return True
                await response.text()
                print(f"   ❌ Status: {status}")
                return False
        except Exception as e:
            print(f"   ❌ Request failed: {type(e).__name__}")
            return False

    async def test_legacy_query_endpoint(self, session: aiohttp.ClientSession):
        """Test the legacy query endpoint."""
        print("🔍 Testing corpus service legacy query endpoint...")

        token = self.generate_valid_jwt()

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with session.post(
                f"{self.base_url}/api/v1/query/?query_text=What is cybersecurity?&top_k=3",
                headers=headers,
            ) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {status}")
                    print(f"   Results: {len(data.get('results', []))}")
                    return True
                await response.text()
                print(f"   ❌ Status: {status}")
                return False
        except Exception as e:
            print(f"   ❌ Request failed: {type(e).__name__}")
            return False

    async def test_documents_stats(self, session: aiohttp.ClientSession):
        """Test the documents statistics endpoint."""
        print("🔍 Testing documents statistics endpoint...")

        token = self.generate_valid_jwt()

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with session.get(
                f"{self.base_url}/api/v1/documents/stats", headers=headers
            ) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {status}")
                    print(f"   Total documents: {data.get('total_documents', 'N/A')}")
                    print(f"   Total size: {data.get('total_size_bytes', 'N/A')} bytes")
                    return True
                await response.text()
                print(f"   ❌ Status: {status}")
                return False
        except Exception as e:
            print(f"   ❌ Request failed: {type(e).__name__}")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Corpus Service Tests")
        print("=" * 70)

        async with aiohttp.ClientSession() as session:
            results = {}

            # Test 1: Health check
            results["health"] = await self.test_health_endpoint(session)
            print()

            # Test 2: Documents stats
            results["documents_stats"] = await self.test_documents_stats(session)
            print()

            # Test 3: Semantic search endpoint (calls embedding service)
            results["semantic_search"] = await self.test_semantic_search_endpoint(session)
            print()

            # Test 4: Legacy query endpoint
            results["legacy_query"] = await self.test_legacy_query_endpoint(session)
            print()

            # Summary
            print("📊 Test Results Summary:")
            print("=" * 70)
            for test_name, success in results.items():
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {test_name}: {status}")

            print()
            if all(results.values()):
                print("🎉 All corpus service tests passed!")
                print("💡 The 422 validation errors have been resolved!")
            else:
                print("⚠️  Some tests failed. Check the output above for details.")

            return results


async def main():
    """Main test function."""
    tester = RetrievalServiceTester()
    results = await tester.run_all_tests()

    # Exit with error code if any tests failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Corpus Service Endpoints")
    print("Make sure the corpus service is running on localhost:8003")
    print("And the embedding service is running on localhost:8002")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}")
        sys.exit(1)
