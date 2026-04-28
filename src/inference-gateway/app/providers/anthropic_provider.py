"""
Anthropic Claude provider adapter.

Anthropic API is significantly different from OpenAI.
Requires request/response translation.

Key differences:
- POST /v1/messages (not /v1/chat/completions)
- Different message format (system messages separate)
- Different streaming format
- No native embeddings support
- Different parameter names (max_tokens vs max_completion_tokens)

For production, recommend using via LiteLLM which handles translation.
"""

import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..models.embedding_request import EmbeddingRequest
from ..models.requests import ChatCompletionRequest
from ..models.response_request import ResponseRequest
from ..models.responses import ChatCompletionResponse, ChatCompletionStreamChunk
from ..providers.base import ProviderConfig
from ..utils.errors import (
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = configure_logging(service_name="anthropic_provider")


class AnthropicProvider:
    """
    Anthropic Claude API client.

    Implements Provider protocol with OpenAI format translation.

    **RECOMMENDATION:** Use Anthropic via LiteLLM instead of direct integration.
    LiteLLM provides robust translation and is maintained by the community.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration from database
                - base_url: https://api.anthropic.com
                - api_key: Anthropic API key (x-api-key header)
                - anthropic_version: API version (e.g., "2023-06-01")
        """
        self.name = config.name
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout_seconds
        self.anthropic_version = getattr(config, "anthropic_version", "2023-06-01")

        # Anthropic uses x-api-key header
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

        logger.debug(
            "Initialized Anthropic provider",
            extra={
                "provider_name": self.name,
                "base_url": self.base_url,
                "version": self.anthropic_version,
            },
        )

    def _translate_request_to_anthropic(self, request: ChatCompletionRequest) -> dict[str, Any]:
        """
        Translate OpenAI request format to Anthropic format.

        OpenAI format:
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }

        Anthropic format:
        {
            "model": "claude-3-opus-20240229",
            "system": "You are helpful",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }

        Args:
            request: OpenAI-compatible request

        Returns:
            Anthropic-compatible request dict
        """
        # Extract system message (Anthropic handles it separately)
        system_content = None
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                # Combine multiple system messages
                if msg.content:  # Only add non-empty content
                    if system_content:
                        system_content += "\n" + msg.content
                    else:
                        system_content = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content or ""})

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,  # Anthropic requires max_tokens
        }

        # Add system message if present
        if system_content:
            payload["system"] = system_content

        # Optional parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        # Note: Anthropic doesn't support all OpenAI parameters
        # (frequency_penalty, presence_penalty, etc.)

        return payload

    def _translate_response_from_anthropic(
        self, anthropic_response: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Translate Anthropic response to OpenAI format.

        Anthropic format:
        {
            "id": "msg_abc123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-opus-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }

        OpenAI format:
        {
            "id": "chatcmpl-abc123",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "claude-3-opus-20240229",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }

        Args:
            anthropic_response: Anthropic API response

        Returns:
            OpenAI-compatible response dict
        """
        # Extract text content
        content = ""
        if "content" in anthropic_response:
            for block in anthropic_response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")

        # Map stop_reason to finish_reason
        finish_reason_map = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
        }
        finish_reason = finish_reason_map.get(anthropic_response.get("stop_reason", ""), "stop")

        # Build OpenAI-compatible response
        openai_response = {
            "id": anthropic_response.get("id", "chatcmpl-unknown"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": anthropic_response.get("model", "claude"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
        }

        # Add usage info
        if "usage" in anthropic_response:
            usage = anthropic_response["usage"]
            openai_response["usage"] = {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            }

        return openai_response

    async def chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> ChatCompletionResponse:
        """
        Execute synchronous chat completion via Anthropic.

        Args:
            request: OpenAI-compatible request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response (translated from Anthropic format)

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Anthropic
            ProviderRateLimitError: Rate limit exceeded
        """
        start_time = time.time()

        # Translate request
        payload = self._translate_request_to_anthropic(request)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Calling Anthropic messages API",
            extra={
                "provider": self.name,
                "model": request.model,
                "messages": len(request.messages),
                "request_id": request_id,
            },
        )

        try:
            response = await self.client.post("/v1/messages", json=payload, headers=headers)
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            anthropic_data = response.json()

            # Translate response to OpenAI format
            openai_data = self._translate_response_from_anthropic(anthropic_data)

            logger.debug(
                "Anthropic request completed",
                extra={
                    "provider": self.name,
                    "model": request.model,
                    "latency_ms": latency_ms,
                },
            )

            return ChatCompletionResponse(**openai_data)

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("retry-after")
                retry_seconds = int(retry_after) if retry_after else None
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            error_detail = self._extract_error_detail(e.response)
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def stream_chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> AsyncGenerator[ChatCompletionStreamChunk, None]:
        """
        Execute streaming chat completion via Anthropic.

        **COMPLEX:** Anthropic streaming format is very different from OpenAI.
        For production, strongly recommend using LiteLLM instead.

        Args:
            request: OpenAI-compatible request
            request_id: Optional request ID for tracing

        Yields:
            ChatCompletionStreamChunk: Translated from Anthropic format

        Raises:
            ProviderHTTPError: Streaming not fully implemented (501)
        """
        logger.warning(
            "Anthropic streaming translation is complex - recommend using LiteLLM",
            extra={"provider": self.name, "model": request.model},
        )

        # For production, use LiteLLM
        raise ProviderHTTPError(
            self.name,
            501,
            "Anthropic streaming requires complex translation - use via LiteLLM",
        )

    async def create_embeddings(
        self, request: EmbeddingRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate embeddings.

        **NOT SUPPORTED:** Anthropic does not provide embeddings API.
        Use OpenAI, Mistral, or other embedding providers instead.

        Args:
            request: Embedding request
            request_id: Optional request ID

        Raises:
            ProviderHTTPError: Not supported (501)
        """
        logger.warning(
            "Anthropic does not support embeddings",
            extra={"provider": self.name, "model": request.model},
        )

        raise ProviderHTTPError(self.name, 501, "Anthropic does not provide embeddings API")

    async def create_response(
        self, request: ResponseRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Create stateful response.

        Anthropic doesn't support /v1/responses natively.
        LiteLLM provides translation.

        Args:
            request: Response request
            request_id: Optional request ID

        Raises:
            ProviderHTTPError: Not natively supported (501)
        """
        logger.warning(
            "Anthropic /v1/responses requires LiteLLM translation",
            extra={"provider": self.name, "model": request.model},
        )

        raise ProviderHTTPError(
            self.name,
            501,
            "Anthropic /v1/responses not natively supported - use via LiteLLM",
        )

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract error detail from Anthropic error response."""
        try:
            data = response.json()
            if isinstance(data, dict) and "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
            return response.text[:200]
        except Exception:
            return response.text[:200]

    async def health_check(self) -> bool:
        """
        Check Anthropic provider health.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Simple test request with minimal tokens
            test_payload = {
                "model": "claude-3-haiku-20240307",  # Fastest/cheapest model
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }
            response = await self.client.post("/v1/messages", json=test_payload, timeout=5.0)
            response.raise_for_status()
            logger.debug(f"Anthropic provider {self.name} health check: OK")
            return True
        except Exception as e:
            logger.warning(
                f"Anthropic provider {self.name} health check failed",
                extra={"error": str(e)},
            )
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "AnthropicProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
