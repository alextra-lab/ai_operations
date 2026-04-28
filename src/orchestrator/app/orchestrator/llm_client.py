"""
LLM Client implementation for AI Operations Platform.

This module provides the LLMClient class which handles:
- Direct communication with OpenAI-compatible LLM services
- Retry logic for failed requests
- Both synchronous and streaming API calls
- Timeout and error handling
"""

import os
import time
from collections.abc import AsyncGenerator
from typing import Any, cast

import backoff
import httpx  # Import httpx for granular timeout configuration
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="llm_client", log_level="INFO", log_format="json")

# Re-export BadRequestError for use in other modules
__all__ = ["BadRequestError", "LLMClient"]


class LLMClient:
    """
    Client for making requests to OpenAI-compatible LLM services.
    Handles both synchronous and streaming API calls with retry logic.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        connect_timeout: int = 10,
        read_timeout: int = 300,
        write_timeout: int = 10,
        pool_timeout: int = 5,
        max_retries: int = 3,
        base_delay: int = 1,
    ):
        """
        Initialize the LLM Client with connection parameters.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for API requests (defaults to OpenAI's API)
            connect_timeout: Timeout for establishing connection (seconds)
            read_timeout: Timeout for reading response (seconds)
            write_timeout: Timeout for writing request (seconds)
            pool_timeout: Timeout for connection pool (seconds)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("LLMClient.__init__ START")

        self.api_key = api_key
        if not self.api_key:
            if os.environ.get("PYTEST_CURRENT_TEST"):
                logger.error("LLMClient.__init__ FAILED: No API key found before ValueError")
            raise ValueError("OpenAI API key must be provided")

        # Diagnostic for tests
        if os.environ.get("PYTEST_CURRENT_TEST"):  # Check if running under pytest
            expected_api_key = "test_openai_api_key_for_backend_tests"
            if self.api_key != expected_api_key:
                logger.error("LLMClient.__init__ FAILED: API key mismatch (test key expected)")
                raise ValueError("LLMClient INIT FAILED: API key mismatch (test key expected)")
            logger.info("LLMClient.__init__: API key matches expected test key")

        # Initialize OpenAI client with timeouts
        timeout_config = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=write_timeout,
            pool=pool_timeout,
        )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=timeout_config,
            max_retries=0,  # We'll handle retries ourselves
        )

        # Also initialize the async client for streaming
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=timeout_config,
            max_retries=0,  # We'll handle retries ourselves
        )

        # Configure timeout settings
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.pool_timeout = pool_timeout

        # Configure retry settings
        self.max_retries = max_retries
        self.base_delay = base_delay

        logger.info("LLMClient initialized")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("LLMClient.__init__ END")

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APITimeoutError, APIConnectionError),
        max_tries=3,  # Fixed value instead of lambda
        base=1,  # Fixed value instead of lambda
        on_backoff=lambda details: logger.warning(
            "Retry attempt %d after %.2fs",
            details.get("tries", 0),
            details.get("wait", 0),
        ),
    )
    def make_completion_request(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletion:
        """
        Makes a synchronous API call to OpenAI with retry logic.

        Args:
            model: The OpenAI model name to use
            messages: The messages to send to the API
            temperature: The sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice strategy
            response_format: Optional response format constraint

        Returns:
            The API response
        """
        start_time = time.time()
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,  # type: ignore
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": self.read_timeout,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            logger.debug("API call successful in %.2fs", time.time() - start_time)
            return cast("ChatCompletion", response)
        except Exception as e:
            logger.error("API call failed after %.2fs: %s", time.time() - start_time, str(e))
            raise

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APITimeoutError, APIConnectionError),
        max_tries=3,  # Fixed value instead of lambda
        base=1,  # Fixed value instead of lambda
        on_backoff=lambda details: logger.warning(
            "Async retry attempt %d after %.2fs",
            details.get("tries", 0),
            details.get("wait", 0),
        ),
    )
    async def make_async_completion_request(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletion:
        """
        Makes an asynchronous API call to OpenAI with retry logic.

        Args:
            model: The OpenAI model name to use
            messages: The messages to send to the API
            temperature: The sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice strategy
            response_format: Optional response format constraint

        Returns:
            The API response
        """
        start_time = time.time()
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,  # type: ignore
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": self.read_timeout,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
            if response_format:
                kwargs["response_format"] = response_format

            response = await self.async_client.chat.completions.create(**kwargs)
            logger.debug("Async API call successful in %.2fs", time.time() - start_time)
            return cast("ChatCompletion", response)
        except Exception as e:
            logger.error(
                "Async API call failed after %.2fs: %s",
                time.time() - start_time,
                str(e),
            )
            raise

    async def make_streaming_completion_request(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Makes a streaming API call to OpenAI.

        Args:
            model: The OpenAI model name to use
            messages: The messages to send to the API
            temperature: The sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice strategy
            response_format: Optional response format constraint

        Returns:
            An AsyncStream for the streaming response
        """
        # Create the streaming response
        try:
            logger.info("Making streaming API call to model: %s", model)
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,  # type: ignore
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                "timeout": self.read_timeout,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
            if response_format:
                kwargs["response_format"] = response_format

            stream = await self.async_client.chat.completions.create(**kwargs)
            logger.info("Streaming API call successful to model %s", model)
            async for chunk in stream:
                yield chunk
        except Exception as e:
            logger.error(
                "Streaming API call failed with detailed error: %s: %s",
                type(e).__name__,
                str(e),
            )
            # Re-raise the exception so it can be handled by the calling code
            raise
