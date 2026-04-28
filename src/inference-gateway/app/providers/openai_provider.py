"""
OpenAI provider adapter.

Calls OpenAI API using httpx AsyncClient.
Follows ADR-050 (dumb pipe) and ADR-054 (error taxonomy).

VERIFICATION:
- Uses httpx.AsyncClient (existing pattern from embedding service)
- Returns OpenAI-compatible responses
- Error handling with proper exception mapping
- Request ID propagation
- SSE streaming support (P1-T6)
- Retry logic with exponential backoff (P2-T3)
"""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..models.embedding_request import EmbeddingRequest
from ..models.requests import ChatCompletionRequest
from ..models.response_request import ResponseRequest
from ..models.responses import ChatCompletionResponse, ChatCompletionStreamChunk
from ..providers.base import BaseProvider, ProviderConfig
from ..utils.errors import (
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = configure_logging(service_name="openai_provider")


class OpenAIProvider(BaseProvider):
    """
    OpenAI API client with retry logic.

    Implements Provider protocol for OpenAI-compatible endpoints.
    Extends BaseProvider for automatic retry on transient errors.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration from database
        """
        super().__init__(config)

        # Create httpx client (reuse pattern from embedding service)
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

        logger.debug(
            "Initialized OpenAI provider",
            extra={
                "provider_name": self.name,
                "base_url": self.base_url,
                "timeout": self.timeout,
            },
        )

    async def chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> ChatCompletionResponse:
        """
        Execute synchronous chat completion.

        Args:
            request: OpenAI-compatible request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from OpenAI
            ProviderRateLimitError: Rate limit exceeded
        """
        start_time = time.time()

        # Build request payload
        payload = request.model_dump(exclude_none=True)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Calling OpenAI chat completions",
            extra={
                "provider": self.name,
                "model": request.model,
                "messages": len(request.messages),
                "stream": request.stream,
                "request_id": request_id,
            },
        )

        assert self.client is not None, "Client not initialized"

        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                "OpenAI request completed",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "latency_ms": latency_ms,
                    "status_code": response.status_code,
                },
            )

            # Parse and validate response
            data = response.json()
            return ChatCompletionResponse(**data)

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "OpenAI request timeout",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "timeout_seconds": self.timeout,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Handle rate limiting
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                logger.warning(
                    "OpenAI rate limit exceeded",
                    extra={
                        "provider": self.name,
                        "model": request.model,
                        "retry_after": retry_seconds,
                        "latency_ms": latency_ms,
                    },
                )
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            # Generic HTTP error
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                "OpenAI HTTP error",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "status_code": e.response.status_code,
                    "error": error_detail,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def stream_chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> AsyncGenerator[ChatCompletionStreamChunk, None]:
        """
        Execute streaming chat completion with SSE.

        Args:
            request: OpenAI-compatible request with stream=true
            request_id: Optional request ID for tracing

        Yields:
            ChatCompletionStreamChunk: Stream chunks with deltas

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from OpenAI
            ProviderRateLimitError: Rate limit exceeded

        Example:
            ```python
            async for chunk in provider.stream_chat_completion(request):
                content = chunk.choices[0]["delta"].get("content", "")
                # process content (do not log or print user/assistant text)
            ```
        """
        start_time = time.time()

        # Build request payload with stream=true
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True  # Ensure streaming is enabled

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Starting OpenAI streaming chat completion",
            extra={
                "provider": self.name,
                "model": request.model,
                "messages": len(request.messages),
                "request_id": request_id,
            },
        )

        assert self.client is not None, "Client not initialized"

        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()

                chunk_count = 0
                async for line in response.aiter_lines():
                    # Skip empty lines
                    if not line or not line.strip():
                        continue

                    # SSE format: "data: {json}\n\n"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        # Check for [DONE] signal
                        if data_str.strip() == "[DONE]":
                            latency_ms = int((time.time() - start_time) * 1000)
                            logger.debug(
                                "OpenAI streaming completed",
                                extra={
                                    "provider": self.name,
                                    "model": request.model,
                                    "chunks": chunk_count,
                                    "latency_ms": latency_ms,
                                },
                            )
                            break

                        # Parse and yield chunk
                        try:
                            data = json.loads(data_str)
                            chunk = ChatCompletionStreamChunk(**data)
                            chunk_count += 1
                            yield chunk

                        except json.JSONDecodeError as e:
                            logger.warning(
                                "Failed to parse streaming chunk",
                                extra={
                                    "provider": self.name,
                                    "error": str(e),
                                    "data": data_str[:100],
                                },
                            )
                            continue

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "OpenAI streaming timeout",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "timeout_seconds": self.timeout,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Handle rate limiting
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                logger.warning(
                    "OpenAI streaming rate limit exceeded",
                    extra={
                        "provider": self.name,
                        "model": request.model,
                        "retry_after": retry_seconds,
                        "latency_ms": latency_ms,
                    },
                )
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            # Generic HTTP error
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                "OpenAI streaming HTTP error",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "status_code": e.response.status_code,
                    "error": error_detail,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def create_embeddings(
        self, request: EmbeddingRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate embeddings for text input.

        CRITICAL for RAG functionality:
        - Document ingestion (vector generation)
        - Semantic search queries
        - Similarity scoring

        Args:
            request: Embedding request (model, input, options)
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible embedding response dict:
            {
                "object": "list",
                "data": [{"object": "embedding", "embedding": [...], "index": 0}],
                "model": "...",
                "usage": {"prompt_tokens": X, "total_tokens": X}
            }

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from provider
            ProviderRateLimitError: Rate limit exceeded

        Example:
            ```python
            request = EmbeddingRequest(
                model="bge-embeddings",
                input="What is cybersecurity?"
            )
            response = await provider.create_embeddings(request)
            embeddings = response["data"][0]["embedding"]
            ```
        """
        start_time = time.time()

        # Build request payload
        payload = request.model_dump(exclude_none=True)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        input_count = len(request.input) if isinstance(request.input, list) else 1
        logger.debug(
            "Calling OpenAI embeddings",
            extra={
                "provider": self.name,
                "model": request.model,
                "input_count": input_count,
                "request_id": request_id,
            },
        )

        assert self.client is not None, "Client not initialized"

        try:
            response = await self.client.post(
                "/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            data: dict[str, Any] = response.json()

            logger.debug(
                "OpenAI embeddings completed",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "embedding_count": len(data.get("data", [])),
                    "latency_ms": latency_ms,
                    "status_code": response.status_code,
                },
            )

            return data

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "OpenAI embeddings timeout",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "timeout_seconds": self.timeout,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Handle rate limiting
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                logger.warning(
                    "OpenAI embeddings rate limit exceeded",
                    extra={
                        "provider": self.name,
                        "model": request.model,
                        "retry_after": retry_seconds,
                        "latency_ms": latency_ms,
                    },
                )
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            # Generic HTTP error
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                "OpenAI embeddings HTTP error",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "status_code": e.response.status_code,
                    "error": error_detail,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def create_response(
        self, request: ResponseRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Create stateful response (OpenAI Responses API).

        NEW OPENAI API (2024+) for agentic workflows:
        - Stateful conversations (automatic state tracking)
        - Multimodal support (text, images, audio)
        - Tool calling
        - No manual history management required

        LiteLLM provides translation for non-native providers
        (Anthropic, Mistral, etc.) via /v1/responses endpoint.

        Args:
            request: Response request (model, messages or previous_response_id)
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response dict:
            {
                "id": "resp_...",
                "object": "response",
                "model": "...",
                "created": 1699000000,
                "role": "assistant",
                "content": [...],
                "stop_reason": "stop",
                "usage": {"input_tokens": X, "output_tokens": Y}
            }

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from provider
            ProviderRateLimitError: Rate limit exceeded

        Example:
            ```python
            # First request
            request = ResponseRequest(
                model="mistral-nemo-2407",
                messages=[{"role": "user", "content": "Analyze this threat"}]
            )
            response = await provider.create_response(request)

            # Continue conversation
            next_request = ResponseRequest(
                model="mistral-nemo-2407",
                previous_response_id=response["id"]
            )
            next_response = await provider.create_response(next_request)
            ```
        """
        start_time = time.time()

        # Build request payload
        payload = request.model_dump(exclude_none=True)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Calling OpenAI responses API",
            extra={
                "provider": self.name,
                "model": request.model,
                "has_previous": bool(request.previous_response_id),
                "has_input": bool(request.input),
                "has_instructions": bool(request.instructions),
                "request_id": request_id,
            },
        )

        assert self.client is not None, "Client not initialized"

        try:
            response = await self.client.post(
                "/responses",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            data: dict[str, Any] = response.json()

            logger.debug(
                "OpenAI responses completed",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "response_id": data.get("id"),
                    "latency_ms": latency_ms,
                    "status_code": response.status_code,
                },
            )

            return data

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "OpenAI responses timeout",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "timeout_seconds": self.timeout,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Handle rate limiting
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                logger.warning(
                    "OpenAI responses rate limit exceeded",
                    extra={
                        "provider": self.name,
                        "model": request.model,
                        "retry_after": retry_seconds,
                        "latency_ms": latency_ms,
                    },
                )
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            # Generic HTTP error
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                "OpenAI responses HTTP error",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "status_code": e.response.status_code,
                    "error": error_detail,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """
        Extract error detail from OpenAI error response.

        OpenAI returns errors in format:
        {
            "error": {
                "message": "...",
                "type": "...",
                "code": "..."
            }
        }
        """
        try:
            data = response.json()
            if isinstance(data, dict) and "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
            return response.text[:200]  # Truncate to 200 chars
        except Exception:
            return response.text[:200]

    async def health_check(self) -> bool:
        """
        Check OpenAI provider health.

        Makes a simple models list request to verify connectivity.

        Returns:
            True if provider is healthy, False otherwise
        """
        if self.client is None:
            return False

        try:
            response = await self.client.get("/models", timeout=5.0)
            response.raise_for_status()
            logger.debug(
                "Provider health check OK",
                extra={"provider": self.name},
            )
            return True
        except Exception as e:
            logger.warning(
                "Provider health check failed",
                extra={"provider": self.name, "error": str(e)},
            )
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()

    async def __aenter__(self) -> "OpenAIProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
