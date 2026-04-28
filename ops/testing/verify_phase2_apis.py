#!/usr/bin/env python3
"""
Phase 2 API Endpoint Verification Script

This script verifies the actual state of Phase 2 API endpoints by:
1. Fetching the OpenAPI specification from the running backend
2. Comparing expected endpoints with actual endpoints
3. Testing endpoint functionality with real API calls
4. Generating a comprehensive status report

Inspired by demonstrate_enhanced_pipeline_fixed.py

Usage:
    python scripts/testing/verify_phase2_apis.py --api-url http://localhost:8006
    python scripts/testing/verify_phase2_apis.py --username testuser --password password --full-test
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import RequestException


# Configure logging
def setup_logging():
    """Set up logging to write to both console and file."""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/phase2_api_verification_{timestamp}.log"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, log_filename


logger, LOG_FILE_PATH = setup_logging()

# Expected Phase 2 API Endpoints based on UI_API_ANALYSIS.md
EXPECTED_ENDPOINTS = {
    "query": {
        "POST /api/v1/query/search": {"status": "should_exist", "ui_calls": True},
        "POST /api/v1/query/ask": {"status": "should_exist", "ui_calls": True},
    },
    "query_history": {
        "GET /api/v1/query-history": {
            "status": "should_exist",
            "ui_calls": True,
            "param_mismatch": True,
        },
        "POST /api/v1/query-history": {"status": "missing", "ui_calls": True},
        "GET /api/v1/query-history/{history_id}": {"status": "should_exist", "ui_calls": False},
        "POST /api/v1/query-history/fork": {"status": "should_exist", "ui_calls": True},
        "PATCH /api/v1/query-history/{history_id}": {"status": "should_exist", "ui_calls": True},
        "DELETE /api/v1/query-history/{history_id}": {"status": "should_exist", "ui_calls": True},
    },
    "documents": {
        "POST /api/v1/documents/": {"status": "should_exist", "ui_calls": True},
        "GET /api/v1/documents/": {"status": "should_exist", "ui_calls": True},
        "GET /api/v1/documents/{document_id}": {"status": "should_exist", "ui_calls": True},
        "PATCH /api/v1/documents/{document_id}": {
            "status": "should_exist",
            "ui_calls": True,
            "ui_uses_wrong_method": "PUT",
        },
        "DELETE /api/v1/documents/{document_id}": {"status": "should_exist", "ui_calls": True},
        "GET /api/v1/documents/{document_id}/status": {"status": "should_exist", "ui_calls": True},
        "GET /api/v1/documents/stats": {"status": "should_exist", "ui_calls": True},
        "POST /api/v1/documents/{document_id}/reprocess": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/{document_id}/analytics": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/{document_id}/versions": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/{document_id}/download": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/{document_id}/preview": {"status": "missing", "ui_calls": True},
        "POST /api/v1/documents/batch": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/classifications": {"status": "missing", "ui_calls": True},
        "GET /api/v1/documents/tags": {"status": "missing", "ui_calls": True},
    },
    "use_cases": {
        "GET /api/v1/use-cases/available": {"status": "should_exist", "ui_calls": True},
        "POST /api/v1/use-cases/{id}/execute": {"status": "missing", "ui_calls": True},
    },
}


class Phase2APIVerifier:
    """Verifies Phase 2 API endpoint status and functionality."""

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access_token: str | None = None
        self.session = requests.Session()
        self.openapi_spec: dict[str, Any] | None = None
        self.verification_results: dict[str, list[Any]] = {
            "working": [],
            "missing": [],
            "param_mismatch": [],
            "unexpected": [],
            "errors": [],
        }
        logger.info(f"Initialized Phase 2 API Verifier with base URL: {self.base_url}")

    def authenticate(self) -> bool:
        """Authenticate with the API."""
        if not self.username or not self.password:
            logger.warning("Username or password not provided. Skipping authentication.")
            return False
        try:
            auth_url = f"{self.base_url}/auth/token"
            auth_data = {"username": self.username, "password": self.password}
            logger.info(f"Authenticating as user: {self.username}")

            response = self.session.post(auth_url, data=auth_data)

            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get("access_token")
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info("✅ Authentication successful")
                return True
            logger.error(f"❌ Authentication failed: {response.status_code}")
            return False
        except RequestException as e:
            logger.error(f"❌ Error during authentication: {e}")
            return False

    def fetch_openapi_spec(self) -> bool:
        """Fetch the OpenAPI specification from the backend."""
        try:
            openapi_url = f"{self.base_url}/openapi.json"
            logger.info(f"Fetching OpenAPI spec from: {openapi_url}")

            response = self.session.get(openapi_url)
            response.raise_for_status()

            spec = response.json()
            self.openapi_spec = spec if isinstance(spec, dict) else {}
            logger.info(
                f"✅ Successfully fetched OpenAPI spec (version: {self.openapi_spec.get('openapi', 'unknown')})"
            )
            return True
        except RequestException as e:
            logger.error(f"❌ Failed to fetch OpenAPI spec: {e}")
            return False

    def extract_actual_endpoints(self) -> dict[str, set[str]]:
        """Extract actual endpoints from OpenAPI spec organized by HTTP method."""
        if not self.openapi_spec or "paths" not in self.openapi_spec:
            return {}

        endpoints_by_method: dict[str, set[str]] = defaultdict(set)
        paths = self.openapi_spec.get("paths") or {}

        for path, methods in paths.items():
            for method in methods:
                if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                    endpoint = f"{method.upper()} {path}"
                    endpoints_by_method[method.upper()].add(endpoint)

        return dict(endpoints_by_method)

    def normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint path for comparison (handle path parameters)."""
        # Replace specific parameter names with generic {id} pattern
        import re

        return re.sub(r"\{[^}]+\}", "{id}", endpoint)

    def verify_endpoints(self) -> dict[str, Any]:
        """Verify expected endpoints against actual OpenAPI spec."""
        if not self.openapi_spec:
            logger.error("OpenAPI spec not loaded. Cannot verify endpoints.")
            return self.verification_results

        actual_endpoints = self.extract_actual_endpoints()
        all_actual: set[str] = set()
        for method_endpoints in actual_endpoints.values():
            all_actual.update(method_endpoints)

        logger.info(f"\n{'=' * 80}\nENDPOINT VERIFICATION RESULTS\n{'=' * 80}")

        # Check each expected endpoint
        for category, endpoints in EXPECTED_ENDPOINTS.items():
            logger.info(f"\n--- {category.upper()} ENDPOINTS ---")

            for endpoint, metadata in endpoints.items():
                # Normalize for comparison
                normalized = self.normalize_endpoint(endpoint)

                # Check if endpoint exists in actual spec
                found = False
                for actual in all_actual:
                    if self.normalize_endpoint(actual) == normalized:
                        found = True
                        break

                if found:
                    if metadata["status"] == "missing":
                        logger.info(
                            f"✅ FIXED: {endpoint} (was expected to be missing, now exists!)"
                        )
                        self.verification_results["working"].append(
                            {
                                "endpoint": endpoint,
                                "category": category,
                                "note": "Previously missing, now implemented",
                            }
                        )
                    else:
                        logger.info(f"✅ EXISTS: {endpoint}")
                        result = {
                            "endpoint": endpoint,
                            "category": category,
                            "ui_calls": metadata.get("ui_calls", False),
                        }

                        if metadata.get("param_mismatch"):
                            logger.warning(
                                "   ⚠️  Parameter mismatch: UI sends wrong parameter names"
                            )
                            self.verification_results["param_mismatch"].append(result)
                        elif metadata.get("ui_uses_wrong_method"):
                            logger.warning(
                                f"   ⚠️  UI uses wrong HTTP method: {metadata['ui_uses_wrong_method']} instead of {endpoint.split()[0]}"
                            )
                            self.verification_results["param_mismatch"].append(result)
                        else:
                            self.verification_results["working"].append(result)
                else:
                    if metadata["status"] == "missing":
                        logger.warning(f"❌ MISSING (expected): {endpoint}")
                    else:
                        logger.error(f"❌ MISSING (unexpected): {endpoint}")

                    self.verification_results["missing"].append(
                        {
                            "endpoint": endpoint,
                            "category": category,
                            "ui_calls": metadata.get("ui_calls", False),
                            "expected_status": metadata["status"],
                        }
                    )

        # Check for unexpected endpoints (not in our expected list)
        all_expected = set()
        for endpoints in EXPECTED_ENDPOINTS.values():
            for endpoint in endpoints:
                all_expected.add(self.normalize_endpoint(endpoint))

        for actual in all_actual:
            normalized = self.normalize_endpoint(actual)
            if normalized not in all_expected and any(
                x in actual for x in ["/query", "/documents", "/use-case"]
            ):
                logger.info(f"(i) UNEXPECTED: {actual} (not in Phase 2 spec)")
                self.verification_results["unexpected"].append(actual)

        return self.verification_results

    def test_endpoint_functionality(self, endpoint: str) -> tuple[bool, str]:
        """Test if an endpoint is actually functional (requires auth)."""
        if not self.access_token:
            return False, "No authentication token"

        method, path = endpoint.split(" ", 1)
        url = f"{self.base_url}{path}"

        try:
            # For endpoints with path parameters, skip functional testing
            if "{" in path:
                return True, "Skipped (path parameters required)"

            # Only test GET endpoints for safety
            if method == "GET":
                response = self.session.get(url)
                if response.status_code < 500:
                    return True, f"HTTP {response.status_code}"
                return False, f"HTTP {response.status_code}"
            return True, "Skipped (non-GET method)"
        except RequestException as e:
            return False, str(e)

    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        results = self.verification_results

        print(f"\n{'=' * 80}")
        print("PHASE 2 API VERIFICATION SUMMARY")
        print(f"{'=' * 80}")

        total_expected = sum(len(endpoints) for endpoints in EXPECTED_ENDPOINTS.values())
        working_count = len(results["working"])
        missing_count = len(results["missing"])
        mismatch_count = len(results["param_mismatch"])

        print("\n📊 OVERALL STATUS:")
        print(f"  Total Expected Endpoints: {total_expected}")
        print(f"  ✅ Working: {working_count}")
        print(f"  ❌ Missing: {missing_count}")
        print(f"  ⚠️  Parameter/Method Mismatches: {mismatch_count}")
        print(f"  (i) Unexpected: {len(results['unexpected'])}")

        completion_percentage = (working_count / total_expected * 100) if total_expected > 0 else 0
        print(f"\n🎯 API Completion: {completion_percentage:.1f}%")

        if completion_percentage >= 80:
            print("   Status: ✅ GOOD - Most endpoints implemented")
        elif completion_percentage >= 60:
            print("   Status: ⚠️  FAIR - Significant gaps remain")
        else:
            print("   Status: ❌ POOR - Major implementation needed")

        # Missing endpoints by category
        if results["missing"]:
            print(f"\n❌ MISSING ENDPOINTS ({missing_count}):")
            by_category = defaultdict(list)
            for item in results["missing"]:
                by_category[item["category"]].append(item["endpoint"])

            for category, endpoints in sorted(by_category.items()):
                print(f"\n  {category.upper()}:")
                for endpoint in endpoints:
                    print(f"    • {endpoint}")

        # Parameter mismatches
        if results["param_mismatch"]:
            print(f"\n⚠️  PARAMETER/METHOD MISMATCHES ({mismatch_count}):")
            for item in results["param_mismatch"]:
                print(f"  • {item['endpoint']}")

        # Critical issues
        print("\n🔴 CRITICAL ISSUES:")
        critical_missing = [
            item
            for item in results["missing"]
            if item["ui_calls"] and item["expected_status"] == "should_exist"
        ]

        if critical_missing:
            print(f"  {len(critical_missing)} endpoints that UI calls are missing:")
            for item in critical_missing[:5]:  # Show first 5
                print(f"    • {item['endpoint']}")
        else:
            print("  ✅ No critical issues - all UI-called endpoints exist")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")

        if missing_count > 0:
            print(f"  1. Implement {missing_count} missing endpoints (see list above)")

        if mismatch_count > 0:
            print(f"  2. Fix {mismatch_count} parameter/method mismatches in UI")

        if critical_missing:
            print(
                f"  3. PRIORITY: Fix {len(critical_missing)} critical missing endpoints that UI calls"
            )

        print("  4. Run full functional tests with authentication")
        print("  5. Update UI_API_ANALYSIS.md with current status")

        print(f"\n📋 Detailed log saved to: {LOG_FILE_PATH}")
        print(f"{'=' * 80}\n")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify Phase 2 API endpoint status against expected implementation."
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_BASE_URL", "http://localhost:8006"),
        help="Base URL of the backend API",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("API_USERNAME"),
        help="Username for authentication (optional)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("API_PASSWORD"),
        help="Password for authentication (optional)",
    )
    parser.add_argument(
        "--full-test", action="store_true", help="Run full functional tests (requires auth)"
    )
    parser.add_argument("--output-json", help="Save results to JSON file")
    return parser.parse_args()


def main():
    """Main entry point for Phase 2 API verification."""
    logger.info("Starting Phase 2 API Verification")
    logger.info(f"Log output will be saved to: {LOG_FILE_PATH}")

    print(f"\n{'=' * 80}")
    print("PHASE 2 API ENDPOINT VERIFICATION")
    print(f"{'=' * 80}")
    print("This script verifies the actual state of Phase 2 API endpoints")
    print("by comparing expected endpoints with the OpenAPI specification.")
    print(f"\n📋 Log file: {LOG_FILE_PATH}\n")

    args = parse_args()
    verifier = Phase2APIVerifier(args.api_url, args.username, args.password)

    # Fetch OpenAPI spec
    if not verifier.fetch_openapi_spec():
        logger.error("Failed to fetch OpenAPI spec. Exiting.")
        sys.exit(1)

    # Authenticate if credentials provided
    if args.username and args.password:
        verifier.authenticate()

    # Verify endpoints
    results = verifier.verify_endpoints()

    # Run functional tests if requested
    if args.full_test and verifier.access_token:
        logger.info(f"\n{'=' * 80}\nFUNCTIONAL TESTING\n{'=' * 80}")
        for item in results["working"]:
            endpoint = item["endpoint"]
            success, message = verifier.test_endpoint_functionality(endpoint)
            status = "✅" if success else "❌"
            logger.info(f"{status} {endpoint}: {message}")

    # Generate summary report
    verifier.generate_summary_report()

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {args.output_json}")

    logger.info("Phase 2 API Verification completed")


if __name__ == "__main__":
    main()
