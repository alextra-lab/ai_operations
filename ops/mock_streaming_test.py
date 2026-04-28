#!/usr/bin/env python3
"""
Mock Streaming Test Script for AI Operations Platform.

This script provides a standalone test to validate the streaming capability
by mocking the OpenAI API response. It isolates the streaming infrastructure
from the actual LLM API to help diagnose issues.

Usage:
    python mock_streaming_test.py
"""

import asyncio
import logging
import time

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_streaming_test")

# Sample mock data
MOCK_CHUNKS = [
    "Cybersecurity ",
    "is the practice of ",
    "protecting systems, networks, ",
    "and programs from digital attacks. ",
    "These attacks often aim to access, change, ",
    "or destroy sensitive information, extort money from users, ",
    "or interrupt normal business processes.",
]


class MockResponse:
    """Mock object to simulate OpenAI response structure."""

    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockChoice:
    """Mock object to simulate a choice in OpenAI response."""

    def __init__(self, content):
        self.delta = MockDelta(content)


class MockDelta:
    """Mock object to simulate content delta in streaming response."""

    def __init__(self, content):
        self.content = content


class MockApiServer:
    """
    Mock API server that simulates the OpenAI API for testing streaming.
    """

    async def get_mock_stream(self):
        """Generate a mock stream of data chunks."""
        for chunk in MOCK_CHUNKS:
            # Simulate network latency
            await asyncio.sleep(0.2)
            yield MockResponse(chunk)


class MockAsyncClient:
    """Mock an OpenAI AsyncClient for streaming responses."""

    async def chat(self):
        """Return a mock chat completions namespace."""
        return MockCompletions()


class MockCompletions:
    """Mock the completions interface of OpenAI API."""

    async def create(self, **kwargs):
        """
        Mock create method that returns an async generator with chunks.

        Args:
            **kwargs: Keyword arguments to simulate API parameters

        Returns:
            An async generator yielding mock chunks
        """
        logger.info(f"Mock API create called with: {kwargs}")

        # Create a mock server
        mock_server = MockApiServer()

        # Return the async generator
        return mock_server.get_mock_stream()


class MockLLMClient:
    """Mock LLM client for testing streaming functionality."""

    def __init__(self):
        self.async_client = MockAsyncClient()
        logger.info("Initialized mock LLM client")

    async def make_streaming_completion_request(
        self, model: str, messages: list[dict[str, str]], temperature: float, max_tokens: int
    ):
        """
        Mock method to simulate streaming API call to OpenAI.

        Args:
            model: The OpenAI model to use (ignored in mock)
            messages: The messages to send (ignored in mock)
            temperature: Sampling temperature (ignored in mock)
            max_tokens: Max tokens to generate (ignored in mock)

        Returns:
            An async generator yielding mock response chunks
        """
        logger.info(f"Making mock streaming API call to model: {model}")
        try:
            # Get chat completions interface
            completions = await self.async_client.chat()

            # Create the streaming response
            stream = await completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            logger.info(f"Mock streaming API call successful for model {model}")
            return stream

        except Exception as e:
            logger.error(f"Mock streaming API call failed: {type(e).__name__}: {e!s}")
            raise


class MockStreamingTest:
    """Test framework for mocking streaming responses."""

    async def test_streaming(self):
        """Run the mock streaming test."""
        logger.info("Starting mock streaming test")

        try:
            # Create the mock client
            client = MockLLMClient()

            # Prepare mock parameters
            model = "gpt-4.1-mini"
            messages = [{"role": "user", "content": "What is cybersecurity?"}]
            temperature = 0.7
            max_tokens = 500

            # Get the mock streaming response
            start_time = time.time()
            stream = await client.make_streaming_completion_request(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )

            # Process the streaming response
            full_response = ""
            chunk_count = 0

            async for chunk in stream:
                chunk_count += 1
                content = chunk.choices[0].delta.content or ""
                full_response += content

                logger.info(f"Chunk {chunk_count}: '{content}'")
                logger.info(f"Response so far: '{full_response}'")

            # Log the final result
            processing_time = time.time() - start_time
            logger.info(f"Completed in {processing_time:.2f}s")
            logger.info(f"Received {chunk_count} chunks")
            logger.info(f"Full response: {full_response}")

            return {
                "success": True,
                "chunks": chunk_count,
                "response": full_response,
                "time": processing_time,
            }

        except Exception as e:
            logger.error(f"Error in test: {e!s}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def run_test():
    """Run the test and print results."""
    test = MockStreamingTest()
    results = await test.test_streaming()

    # Print the results
    print("\n" + "=" * 80)
    print(" MOCK STREAMING TEST RESULTS")
    print("=" * 80)

    if results["success"]:
        print("Success: YES")
        print(f"Chunks Received: {results['chunks']}")
        print(f"Response Length: {len(results['response'])} chars")
        print(f"Total Time: {results['time']:.2f}s")
        print("\nFull Response:")
        print(f"{results['response']}")
    else:
        print("Success: NO")
        print(f"Error Type: {results.get('error_type', 'Unknown')}")
        print(f"Error: {results.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)


def main():
    """Main entry point for the script."""
    # Banner
    print("\n" + "=" * 80)
    print(" MOCK STREAMING TEST - AI Operations Platform")
    print("=" * 80 + "\n")

    # Run the async test
    asyncio.run(run_test())


if __name__ == "__main__":
    main()
