#!/usr/bin/env python3
"""
Test script for OpenAI API key configuration.

This script directly tests the OpenAI API to verify that the API key is working
and can make successful API calls.

Usage:
    python test_openai_key.py [--api-key API_KEY]
"""

import argparse
import json
import logging
import os
from typing import Any

try:
    import pytest

    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

try:
    from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("WARNING: openai package not installed. Install with: pip install openai")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("openai_key_test")


def test_openai_api(api_key: str | None = None):
    """
    Test the OpenAI API with the provided API key or environment variable.

    Args:
        api_key: Optional API key. If not provided, will look for OPENAI_API_KEY environment variable.
    """
    if not HAS_OPENAI:
        pytest.skip("OpenAI package not installed")

    # Get API key from parameter or environment
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("No API key provided and OPENAI_API_KEY not set in environment")

    # Show redacted key for debugging
    logger.info("Testing OpenAI API connectivity")

    # Initialize the client
    client = OpenAI(api_key=key)
    logger.info("Initialized OpenAI client")

    # Test with a simple request
    logger.info("Making test request to OpenAI API...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use a known model for testing
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10,
    )

    # Extract response content
    content = response.choices[0].message.content
    usage = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }

    logger.info(f"API request successful. Response: '{content}'")
    logger.info(f"Token usage: {json.dumps(usage)}")

    # Assertions for pytest
    assert content is not None
    assert len(content) > 0
    assert usage["total_tokens"] > 0

    # Test streaming API
    logger.info("Testing streaming API...")
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Count to 5"}],
        max_tokens=20,
        stream=True,
    )

    # Process streaming response
    stream_content = ""
    chunk_count = 0
    for chunk in stream:
        chunk_count += 1
        delta_content = chunk.choices[0].delta.content or ""
        stream_content += delta_content

    logger.info(f"Streaming API test successful. Received {chunk_count} chunks.")
    logger.info(f"Streaming response: '{stream_content}'")

    # Assertions for streaming
    assert chunk_count > 0
    assert len(stream_content) >= 0  # Stream content might be empty but chunks should exist


def run_openai_test(api_key: str | None = None) -> dict[str, Any]:
    """
    Run OpenAI API test and return results (for non-pytest usage).

    Args:
        api_key: Optional API key. If not provided, will look for OPENAI_API_KEY environment variable.

    Returns:
        Dictionary with test results
    """
    if not HAS_OPENAI:
        return {"success": False, "error": "OpenAI package not installed"}

    # Get API key from parameter or environment
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return {
            "success": False,
            "error": "No API key provided and OPENAI_API_KEY not set in environment",
        }

    # Show redacted key for debugging
    logger.info("Testing OpenAI API connectivity")

    try:
        # Initialize the client
        client = OpenAI(api_key=key)
        logger.info("Initialized OpenAI client")

        # Test with a simple request
        logger.info("Making test request to OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a known model for testing
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
        )

        # Extract response content
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        logger.info(f"API request successful. Response: '{content}'")
        logger.info(f"Token usage: {json.dumps(usage)}")

        # Test streaming API
        logger.info("Testing streaming API...")
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Count to 5"}],
            max_tokens=20,
            stream=True,
        )

        # Process streaming response
        stream_content = ""
        chunk_count = 0
        for chunk in stream:
            chunk_count += 1
            delta_content = chunk.choices[0].delta.content or ""
            stream_content += delta_content

        logger.info(f"Streaming API test successful. Received {chunk_count} chunks.")
        logger.info(f"Streaming response: '{stream_content}'")

        return {
            "success": True,
            "response": content,
            "streaming_response": stream_content,
            "streaming_chunks": chunk_count,
            "usage": usage,
        }

    except APITimeoutError as e:
        logger.error(f"API Timeout Error: {e!s}")
        return {"success": False, "error": f"Timeout error: {e!s}", "type": "timeout"}

    except APIConnectionError as e:
        logger.error(f"API Connection Error: {e!s}")
        return {"success": False, "error": f"Connection error: {e!s}", "type": "connection"}

    except RateLimitError as e:
        logger.error(f"Rate Limit Error: {e!s}")
        return {"success": False, "error": f"Rate limit error: {e!s}", "type": "rate_limit"}

    except Exception as e:
        logger.error(f"Error testing OpenAI API: {e!s}", exc_info=True)
        return {"success": False, "error": f"Error: {e!s}", "type": type(e).__name__}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test OpenAI API key configuration")
    parser.add_argument(
        "--api-key", help="OpenAI API key (if not provided, will use environment variable)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_args()

    # Banner
    print("\n" + "=" * 80)
    print(" OPENAI API KEY TEST")
    print("=" * 80 + "\n")

    # Check for OpenAI package
    if not HAS_OPENAI:
        print("ERROR: The openai package is required for this test.")
        print("Install it with: pip install openai")
        return

    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: No API key provided.")
        print("Either set the OPENAI_API_KEY environment variable or use --api-key")
        return

    # Run the test using the non-pytest version
    results = run_openai_test(api_key)

    # Display results
    print("\n" + "=" * 80)
    print(" TEST RESULTS")
    print("=" * 80)

    if results["success"]:
        print("Success: YES")
        print(f"Simple Response: '{results['response']}'")
        print(f"Streaming Response: '{results['streaming_response']}'")
        print(f"Streaming Chunks: {results['streaming_chunks']}")
        print(f"Token Usage: {json.dumps(results['usage'], indent=2)}")
    else:
        print("Success: NO")
        print(f"Error Type: {results.get('type', 'Unknown')}")
        print(f"Error: {results.get('error', 'Unknown error')}")
        print("\nPossible solutions:")
        print("1. Check if your API key is valid")
        print("2. Verify you have sufficient credits")
        print("3. Check your network connection")
        print("4. Ensure the model name is valid")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
