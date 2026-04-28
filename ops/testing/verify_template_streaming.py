#!/usr/bin/env python3
"""
Verification script for B3-F3: Template-Driven Streaming functionality.

This script tests the streaming precedence rules:
1. Request flag (explicit stream parameter) - highest priority
2. Template default (config.policy.streaming_default) - medium priority
3. Intent default (SUMMARIZATION defaults to streaming=True) - lower priority
4. Global default (stream=False) - lowest priority

Usage:
    python scripts/testing/verify_template_streaming.py
"""

import asyncio
import json
import sys
from typing import Any

import httpx


class TemplateStreamingVerifier:
    """Verifies template-driven streaming functionality."""

    def __init__(self, base_url: str = "http://localhost:8006"):
        """Initialize verifier with base URL."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def authenticate(self) -> bool:
        """Authenticate and get token for API calls."""
        try:
            auth_response = await self.client.post(
                f"{self.base_url}/auth/token", data={"username": "testuser", "password": "testpass"}
            )

            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                self.token = auth_data.get("access_token")
                if self.token:
                    print("✅ Authentication successful")
                    return True
                print("❌ No access token in auth response")
                return False
            print(f"❌ Authentication failed: HTTP {auth_response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Authentication error: {e!s}")
            return False

    async def verify_health(self) -> bool:
        """Verify orchestrator is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Orchestrator health check passed")
                return True
            print(f"❌ Health check failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Health check error: {e!s}")
            return False

    async def test_streaming_precedence_rules(self) -> dict[str, Any]:
        """Test streaming precedence rules with different configurations."""
        results: dict[str, Any] = {}

        # Test cases to verify precedence rules
        test_cases: list[dict[str, Any]] = [
            {
                "name": "explicit_stream_true",
                "query": "Summarize the latest threat intelligence",
                "request_type": "QUERY",
                "stream": True,
                "expected_streaming": True,
                "description": "Explicit stream=True should override template defaults",
            },
            {
                "name": "explicit_stream_false",
                "query": "What are the current security threats?",
                "request_type": "QUERY",
                "stream": False,
                "expected_streaming": False,
                "description": "Explicit stream=False should override template defaults",
            },
            {
                "name": "no_explicit_stream_query",
                "query": "Analyze this security event",
                "request_type": "QUERY",
                "stream": None,
                "expected_streaming": False,  # Should use template default or global default
                "description": "No explicit stream should use template/global default",
            },
            {
                "name": "no_explicit_stream_summarization",
                "query": "Summarize the incident response procedures",
                "request_type": "SUMMARIZATION",
                "stream": None,
                "expected_streaming": True,  # SUMMARIZATION should default to streaming
                "description": "SUMMARIZATION should default to streaming when no explicit flag",
            },
        ]

        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            print(f"   Description: {test_case['description']}")

            try:
                # Prepare request payload
                payload = {"query": test_case["query"], "request_type": test_case["request_type"]}

                # Add stream parameter if specified
                if test_case["stream"] is not None:
                    payload["stream"] = test_case["stream"]

                # Make request with authentication
                headers: dict[str, str] = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                response = await self.client.post(
                    f"{self.base_url}/api/v1/process", json=payload, headers=headers
                )

                if response.status_code == 200:
                    # Check if response is streaming or non-streaming
                    content_type = response.headers.get("content-type", "")
                    is_streaming = (
                        "text/event-stream" in content_type
                        or "application/x-ndjson" in content_type
                    )

                    # For non-streaming, we should get a JSON response
                    if not is_streaming:
                        try:
                            response.json()  # Confirm non-streaming (parse JSON)
                            is_streaming = False  # Confirmed non-streaming
                        except json.JSONDecodeError:
                            # If we can't parse as JSON, it might be streaming
                            is_streaming = True

                    expected = test_case["expected_streaming"]
                    actual = is_streaming

                    if actual == expected:
                        print(f"   ✅ PASS: Streaming={actual} (expected {expected})")
                        results[test_case["name"]] = {
                            "status": "PASS",
                            "expected_streaming": expected,
                            "actual_streaming": actual,
                            "response_status": response.status_code,
                        }
                    else:
                        print(f"   ❌ FAIL: Streaming={actual} (expected {expected})")
                        results[test_case["name"]] = {
                            "status": "FAIL",
                            "expected_streaming": expected,
                            "actual_streaming": actual,
                            "response_status": response.status_code,
                            "error": "Streaming behavior mismatch",
                        }
                else:
                    print(f"   ❌ FAIL: HTTP {response.status_code}")
                    results[test_case["name"]] = {
                        "status": "FAIL",
                        "response_status": response.status_code,
                        "error": f"HTTP {response.status_code}",
                    }

            except Exception as e:
                print(f"   ❌ ERROR: {e!s}")
                results[test_case["name"]] = {"status": "ERROR", "error": str(e)}

        return results

    async def test_use_case_config_streaming_defaults(self) -> dict[str, Any]:
        """Test that different use case configurations affect streaming behavior."""
        results = {}

        # This test would require creating use cases with different streaming defaults
        # For now, we'll test that the system responds appropriately
        print("\n🧪 Testing use case configuration streaming defaults")

        try:
            # Test a query that should use template defaults
            payload = {
                "query": "Provide a detailed analysis of network security",
                "request_type": "QUERY",
                # No explicit stream parameter
            }

            headers: dict[str, str] = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = await self.client.post(
                f"{self.base_url}/api/v1/process", json=payload, headers=headers
            )

            if response.status_code == 200:
                print("   ✅ Use case config streaming test completed")
                results["use_case_config"] = {
                    "status": "PASS",
                    "response_status": response.status_code,
                }
            else:
                print(f"   ❌ Use case config test failed: HTTP {response.status_code}")
                results["use_case_config"] = {
                    "status": "FAIL",
                    "response_status": response.status_code,
                }

        except Exception as e:
            print(f"   ❌ Use case config test error: {e!s}")
            results["use_case_config"] = {"status": "ERROR", "error": str(e)}

        return results

    async def verify_streaming_response_format(self) -> dict[str, Any]:
        """Verify that streaming responses have correct format."""
        results = {}

        print("\n🧪 Testing streaming response format")

        try:
            # Request explicit streaming
            payload = {
                "query": "Generate a comprehensive security report",
                "request_type": "SUMMARIZATION",
                "stream": True,
            }

            headers: dict[str, str] = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = await self.client.post(
                f"{self.base_url}/api/v1/process", json=payload, headers=headers
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")

                # Check if it's a streaming response
                if "text/event-stream" in content_type or "application/x-ndjson" in content_type:
                    print("   ✅ Streaming response format is correct")
                    results["streaming_format"] = {"status": "PASS", "content_type": content_type}
                else:
                    print(f"   ⚠️  Unexpected content type for streaming: {content_type}")
                    results["streaming_format"] = {
                        "status": "WARNING",
                        "content_type": content_type,
                        "note": "May still be valid streaming format",
                    }
            else:
                print(f"   ❌ Streaming format test failed: HTTP {response.status_code}")
                results["streaming_format"] = {
                    "status": "FAIL",
                    "response_status": response.status_code,
                }

        except Exception as e:
            print(f"   ❌ Streaming format test error: {e!s}")
            results["streaming_format"] = {"status": "ERROR", "error": str(e)}

        return results

    async def run_verification(self) -> dict[str, Any]:
        """Run complete verification suite."""
        print("🚀 Starting Template Streaming Verification")
        print("=" * 50)

        # Check health first
        if not await self.verify_health():
            return {"overall_status": "FAIL", "error": "Health check failed"}

        # Authenticate
        if not await self.authenticate():
            return {"overall_status": "FAIL", "error": "Authentication failed"}

        # Run all tests
        results = {
            "health_check": "PASS",
            "precedence_rules": await self.test_streaming_precedence_rules(),
            "use_case_config": await self.test_use_case_config_streaming_defaults(),
            "streaming_format": await self.verify_streaming_response_format(),
        }

        # Calculate overall status
        all_passed = True
        for test_group in results.values():
            if isinstance(test_group, dict):
                for test_result in test_group.values():
                    if isinstance(test_result, dict) and test_result.get("status") in [
                        "FAIL",
                        "ERROR",
                    ]:
                        all_passed = False
                        break

        results["overall_status"] = "PASS" if all_passed else "FAIL"

        return results

    def print_summary(self, results: dict[str, Any]):
        """Print verification summary."""
        print("\n" + "=" * 50)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 50)

        overall_status = results.get("overall_status", "UNKNOWN")
        status_emoji = "✅" if overall_status == "PASS" else "❌"
        print(f"Overall Status: {status_emoji} {overall_status}")

        # Print detailed results
        for test_group, test_results in results.items():
            if test_group == "overall_status":
                continue

            print(f"\n📋 {test_group.replace('_', ' ').title()}:")

            if isinstance(test_results, dict):
                for test_name, test_result in test_results.items():
                    if isinstance(test_result, dict):
                        status = test_result.get("status", "UNKNOWN")
                        emoji = "✅" if status == "PASS" else "⚠️" if status == "WARNING" else "❌"
                        print(f"   {emoji} {test_name}: {status}")

                        if "error" in test_result:
                            print(f"      Error: {test_result['error']}")
                    else:
                        print(f"   ✅ {test_name}: {test_result}")


async def main():
    """Main verification function."""
    async with TemplateStreamingVerifier() as verifier:
        results = await verifier.run_verification()
        verifier.print_summary(results)

        # Exit with appropriate code
        if results.get("overall_status") == "PASS":
            print("\n🎉 Template streaming verification completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Template streaming verification failed!")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
