#!/usr/bin/env python3
"""
Focused test script for streaming functionality in AI Operations Platform.

This script is designed to isolate streaming issues by focusing exclusively on testing
the streaming API endpoint with detailed logging and error tracing.

Usage:
    python test_streaming_only.py
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Any

import requests
from requests.exceptions import RequestException

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("streaming_test")


class StreamingTester:
    """Client for testing streaming functionality."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        username: str | None = None,
        password: str | None = None,
        debug: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.debug = debug
        self.access_token = None
        self.session = requests.Session()

        # Set detailed headers for debugging
        self.session.headers.update(
            {
                "User-Agent": "StreamingTest/1.0",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",  # Important for streaming
            }
        )

        logger.info(f"Initialized StreamingTester for {base_url}")

        if debug:
            # Enable HTTP request debugging
            from http.client import HTTPConnection

            HTTPConnection.debuglevel = 1
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

    def authenticate(self) -> bool:
        """Authenticate with the API and get access token."""
        if not self.username or not self.password:
            logger.warning("No credentials provided - skipping authentication")
            return False

        try:
            auth_url = f"{self.base_url}/auth/token"
            auth_data = {"username": self.username, "password": self.password}

            logger.info(f"Authenticating as {self.username}")
            # Store original content type
            original_content_type = self.session.headers.get("Content-Type")
            # Set form data content type for auth
            self.session.headers["Content-Type"] = "application/x-www-form-urlencoded"

            response = self.session.post(auth_url, data=auth_data)

            # Restore original content type
            if original_content_type:
                self.session.headers["Content-Type"] = original_content_type
            else:
                self.session.headers.pop("Content-Type", None)

            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get("access_token")

                # Add token to session headers
                if self.access_token:
                    self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                    logger.info("Authentication successful")
                    return True
                logger.error("Authentication response missing access_token")
                return False
            logger.error(
                f"Authentication failed with status {response.status_code}: {response.text}"
            )
            return False

        except Exception as e:
            logger.error(f"Authentication error: {e!s}", exc_info=True)
            return False

    def test_streaming(self, query_type: str = "QUERY") -> dict:
        """
        Test streaming functionality with detailed logging.

        Args:
            query_type: The type of query (QUERY, RULE_GENERATION, etc.)

        Returns:
            Dict with test results and diagnostics
        """
        logger.info(f"Testing streaming with {query_type} query")

        # Create query data with more debugging options
        query_data = {
            "query": "What is cybersecurity?",
            "request_type": query_type,
            "stream": True,  # Request streaming response
            "debug_mode": self.debug,  # Pass debug flag to backend
        }

        process_url = f"{self.base_url}/api/v1/process"

        logger.debug(f"Request URL: {process_url}")
        logger.debug(f"Request data: {json.dumps(query_data)}")
        logger.debug(f"Request headers: {json.dumps(dict(self.session.headers))}")

        start_time = time.time()
        results: dict[str, Any] = {
            "success": False,
            "status_code": None,
            "chunks_received": 0,
            "total_content_length": 0,
            "total_time": 0,
            "errors": [],
            "raw_chunks": [],
            "headers": None,
            "metadata": None,
        }

        try:
            # Add debug mode for headers
            if self.debug:
                self.session.headers["X-Debug-Mode"] = "true"
                self.session.headers["X-Trace-ID"] = f"streaming-test-{int(time.time())}"

            # Make streaming request with detailed error handling
            with self.session.post(process_url, json=query_data, stream=True) as response:
                results["status_code"] = response.status_code
                results["headers"] = dict(response.headers)

                logger.info(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {json.dumps(dict(response.headers))}")

                if response.status_code != 200:
                    error_msg = (
                        f"Request failed with status {response.status_code}: {response.text}"
                    )
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    return results

                # Process streaming response with detailed logging
                try:
                    # Parse SSE formatted response
                    for line in response.iter_lines():
                        if not line:
                            continue

                        decoded_line = line.decode("utf-8")
                        results["raw_chunks"].append(decoded_line)
                        logger.debug(f"Raw chunk: {decoded_line}")

                        # Handle SSE format
                        if decoded_line.startswith("data: "):
                            try:
                                chunk_data = json.loads(decoded_line[6:])
                                results["chunks_received"] += 1
                                chunk_response = chunk_data.get("response", "")
                                results["total_content_length"] += len(chunk_response)

                                # Log essential info about this chunk
                                logger.info(
                                    f"Chunk {results['chunks_received']} received: {len(chunk_response)} chars"
                                )
                                if chunk_data.get("metadata", {}).get("is_complete", False):
                                    logger.info("Final chunk received (is_complete=True)")

                                # Extract and log metadata for debugging
                                metadata = chunk_data.get("metadata", {})
                                if metadata:
                                    logger.info(f"Chunk metadata: {json.dumps(metadata)}")
                                    results["metadata"] = metadata  # Store the latest metadata

                                # Log any errors in the chunk
                                if not metadata.get("success", True):
                                    error = metadata.get("error", "Unknown error")
                                    error_type = metadata.get("error_type", "UnknownError")
                                    logger.warning(f"Error in chunk: {error_type} - {error}")
                                    results["errors"].append(f"{error_type}: {error}")
                            except json.JSONDecodeError as e:
                                error_msg = f"JSON decode error in chunk: {e!s}"
                                logger.error(error_msg)
                                results["errors"].append(error_msg)

                    # If we received any chunks, consider it a success
                    results["success"] = results["chunks_received"] > 0
                    logger.info(f"Streaming complete. Received {results['chunks_received']} chunks")

                except Exception as e:
                    error_msg = f"Error processing stream: {e!s}"
                    logger.error(error_msg, exc_info=True)
                    results["errors"].append(error_msg)

        except RequestException as e:
            error_msg = f"Request exception: {e!s}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {e!s}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)

        finally:
            results["total_time"] = time.time() - start_time
            logger.info(f"Test completed in {results['total_time']:.2f}s")

        return results


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test streaming functionality")
    parser.add_argument("--host", default="http://localhost:8000", help="API host URL")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument(
        "--query-type",
        default="QUERY",
        choices=["QUERY", "RULE_GENERATION", "SUMMARIZATION", "ENRICHMENT"],
        help="Type of query to test",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Banner
    print("\n" + "=" * 80)
    print(" STREAMING TEST - AI Operations Platform")
    print("=" * 80 + "\n")

    # Initialize tester
    tester = StreamingTester(
        base_url=args.host,
        username=args.username or os.environ.get("API_USERNAME"),
        password=args.password or os.environ.get("API_PASSWORD"),
        debug=args.debug,
    )

    # Check if credentials were provided
    if not tester.username or not tester.password:
        print("WARNING: No credentials provided. Authentication will be skipped.")
        print(
            "Use --username and --password arguments or API_USERNAME and API_PASSWORD environment variables."
        )
    else:
        # Authenticate
        if not tester.authenticate():
            print("ERROR: Authentication failed. Please check credentials and try again.")
            sys.exit(1)

    # Run test
    print(f"\nTesting streaming with {args.query_type} query type...\n")
    results = tester.test_streaming(args.query_type)

    # Display results
    print("\n" + "=" * 80)
    print(" TEST RESULTS")
    print("=" * 80)
    print(f"Success: {'YES' if results['success'] else 'NO'}")
    print(f"Status Code: {results['status_code']}")
    print(f"Chunks Received: {results['chunks_received']}")
    print(f"Total Response Length: {results['total_content_length']} chars")
    print(f"Total Time: {results['total_time']:.2f}s")

    if results["errors"]:
        print("\nERRORS:")
        for i, error in enumerate(results["errors"], 1):
            print(f"{i}. {error}")

    if results.get("metadata"):
        print("\nMETADATA:")
        for key, value in results["metadata"].items():
            print(f"  {key}: {value}")

    print("\nRAW STREAMING DATA:")
    for i, chunk in enumerate(results["raw_chunks"], 1):
        print(f"Chunk {i}: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
