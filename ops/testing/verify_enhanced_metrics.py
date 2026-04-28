#!/usr/bin/env python3
"""
Verification script for B2-F2: Enhanced Metrics in Response

This script tests the comprehensive metrics implementation by:
1. Making a request to the orchestrator API
2. Verifying all required metrics are present in the response
3. Validating the consolidated confidence score calculation
4. Checking metrics structure and data types

Usage:
    python scripts/testing/verify_enhanced_metrics.py
"""

import sys
from typing import cast

import requests


def get_auth_token() -> str | None:
    """Get authentication token for API requests."""
    try:
        response = requests.post(
            "http://localhost:8006/auth/token",
            data={"username": "testuser", "password": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return cast("str | None", data.get("access_token"))
        print(f"❌ Failed to get auth token: {response.status_code}")
        return None

    except Exception as e:
        print(f"❌ Error getting auth token: {type(e).__name__}")
        return None


def test_enhanced_metrics(token: str) -> bool:
    """
    Test the enhanced metrics implementation.

    Args:
        token: Authentication token

    Returns:
        True if all tests pass, False otherwise
    """
    print("🧪 Testing Enhanced Metrics Implementation...")

    # Test request payload
    test_payload = {"query": "What is threat intelligence?", "request_type": "QUERY"}

    try:
        # Make request to orchestrator
        response = requests.post(
            "http://localhost:8006/api/v1/process",
            json=test_payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            return False

        data = response.json()

        # Verify response structure
        print("✅ API request successful")

        # Check if metrics are present
        if "metrics" not in data:
            print("❌ Missing 'metrics' field in response")
            return False

        metrics = data["metrics"]
        print("✅ Metrics field present in response")

        # Verify consolidated metrics structure
        required_fields = ["retrieval", "guard", "model", "confidence_score", "calculation_method"]
        for field in required_fields:
            if field not in metrics:
                print(f"❌ Missing required field in metrics: {field}")
                return False

        print("✅ All required metrics fields present")

        # Verify retrieval metrics
        retrieval = metrics.get("retrieval")
        if retrieval:
            retrieval_fields = [
                "top_k",
                "hits",
                "avg_similarity",
                "min_similarity",
                "max_similarity",
                "source_count",
            ]
            for field in retrieval_fields:
                if field not in retrieval:
                    print(f"❌ Missing retrieval metric field: {field}")
                    return False

            # Validate data types and ranges
            if not isinstance(retrieval["top_k"], int) or retrieval["top_k"] < 0:
                print("❌ Invalid top_k value")
                return False

            if not isinstance(retrieval["hits"], int) or retrieval["hits"] < 0:
                print("❌ Invalid hits value")
                return False

            if not isinstance(retrieval["avg_similarity"], int | float) or not (
                0 <= retrieval["avg_similarity"] <= 1
            ):
                print("❌ Invalid avg_similarity value")
                return False

            print("✅ Retrieval metrics validated")
        else:
            print("(i) No retrieval metrics (RAG may be disabled)")

        # Verify guard metrics
        guard = metrics.get("guard")
        if guard:
            guard_fields = ["risk_score", "modified", "details"]
            for field in guard_fields:
                if field not in guard:
                    print(f"❌ Missing guard metric field: {field}")
                    return False

            # Validate data types and ranges
            if not isinstance(guard["risk_score"], int | float) or not (
                0 <= guard["risk_score"] <= 1
            ):
                print("❌ Invalid risk_score value")
                return False

            if not isinstance(guard["modified"], bool):
                print("❌ Invalid modified value")
                return False

            print("✅ Guard metrics validated")
        else:
            print("(i) No guard metrics")

        # Verify model metrics
        model = metrics.get("model")
        if model:
            model_fields = [
                "model_id",
                "tokens_in",
                "tokens_out",
                "total_tokens",
                "processing_time",
                "metadata",
            ]
            for field in model_fields:
                if field not in model:
                    print(f"❌ Missing model metric field: {field}")
                    return False

            # Validate data types
            if not isinstance(model["model_id"], str):
                print("❌ Invalid model_id value")
                return False

            if not isinstance(model["total_tokens"], int) or model["total_tokens"] < 0:
                print("❌ Invalid total_tokens value")
                return False

            if (
                not isinstance(model["processing_time"], int | float)
                or model["processing_time"] < 0
            ):
                print("❌ Invalid processing_time value")
                return False

            print("✅ Model metrics validated")
        else:
            print("❌ Model metrics are required")
            return False

        # Verify consolidated confidence score
        confidence_score = metrics.get("confidence_score")
        if not isinstance(confidence_score, int | float) or not (0 <= confidence_score <= 1):
            print("❌ Invalid confidence_score value")
            return False

        print(f"✅ Consolidated confidence score: {confidence_score}")

        # Verify calculation method
        calculation_method = metrics.get("calculation_method")
        if calculation_method != "weighted_consolidation":
            print(f"❌ Unexpected calculation method: {calculation_method}")
            return False

        print("✅ Calculation method validated")

        # Print summary
        print("\n📊 Metrics Summary:")
        print(f"   Confidence Score: {confidence_score:.3f}")
        if retrieval:
            print(f"   Retrieval - Top K: {retrieval['top_k']}, Hits: {retrieval['hits']}")
            print(f"   Retrieval - Avg Similarity: {retrieval['avg_similarity']:.3f}")
            print(
                f"   Retrieval - Min/Max: {retrieval['min_similarity']:.3f}/{retrieval['max_similarity']:.3f}"
            )
        if guard:
            print(
                f"   Guard - Risk Score: {guard['risk_score']:.3f}, Modified: {guard['modified']}"
            )
        if model:
            print(f"   Model - {model['model_id']}")
            print(f"   Model - Tokens: {model['tokens_in']} in, {model['tokens_out']} out")
            print(f"   Model - Processing Time: {model['processing_time']:.2f}s")

        return True

    except Exception as e:
        print(f"❌ Error testing enhanced metrics: {e}")
        return False


def main():
    """Main verification function."""
    print("🚀 Enhanced Metrics Verification Script")
    print("=" * 50)

    # Check if orchestrator is running
    try:
        health_response = requests.get("http://localhost:8006/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Orchestrator is not healthy")
            return 1
    except Exception as e:
        print(f"❌ Cannot connect to orchestrator: {e}")
        return 1

    print("✅ Orchestrator is healthy")

    # Get authentication token
    token = get_auth_token()
    if not token:
        return 1

    print("✅ Authentication successful")

    # Test enhanced metrics
    success = test_enhanced_metrics(token)

    if success:
        print("\n🎉 All Enhanced Metrics Tests Passed!")
        print("✅ B2-F2: Enhanced Metrics in Response - IMPLEMENTATION COMPLETE")
        return 0
    print("\n❌ Enhanced Metrics Tests Failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
