"""
Azure OpenAI provider adapter.

Azure OpenAI Service has different URL structure and authentication
compared to OpenAI Cloud API.

Key differences:
- URL format: https://{resource}.openai.azure.com/openai/deployments/{model}/...
- API key in 'api-key' header instead of 'Authorization: Bearer'
- API version required in query string
- Deployment names instead of model IDs

Example URL:
https://my-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-15-preview
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

logger = configure_logging(service_name="azure_openai_provider")


class AzureOpenAIProvider:
    """
    Azure OpenAI Service API client.

    Implements Provider protocol for Azure-hosted OpenAI models.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize Azure OpenAI provider.

        Args:
            config: Provider configuration from database
                - base_url: Azure resource endpoint (e.g., https://my-resource.openai.azure.com)
                - api_key: Azure API key
                - azure_api_version: API version (e.g., "2024-02-15-preview")
                - timeout_seconds: Request timeout
        """
        self.name = config.name
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout_seconds
        self.api_version = getattr(config, "azure_api_version", "2024-02-15-preview")

        # Azure uses 'api-key' header instead of Bearer token
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

        logger.debug(
            "Initialized Azure OpenAI provider",
            extra={
                "provider_name": self.name,
                "base_url": self.base_url,
                "api_version": self.api_version,
            },
        )

    def _build_deployment_url(self, model: str, endpoint: str) -> str:
        """
        Build Azure deployment URL.

        Azure format: /openai/deployments/{deployment-name}/{endpoint}?api-version={version}

        Args:
            model: Deployment name (Azure's equivalent of model ID)
            endpoint: API endpoint (e.g., "chat/completions", "embeddings")

        Returns:
            Full URL path with query parameters
        """
        return f"/openai/deployments/{model}/{endpoint}?api-version={self.api_version}"

    async def chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> ChatCompletionResponse:
        """
        Execute synchronous chat completion via Azure.

        Args:
            request: OpenAI-compatible request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Azure
            ProviderRateLimitError: Rate limit exceeded
        """
        start_time = time.time()

        # Build Azure-specific URL
        url = self._build_deployment_url(request.model, "chat/completions")

        # Build request payload
        payload = request.model_dump(exclude_none=True)
        # Remove model from payload (it's in the URL)
        payload.pop("model", None)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Calling Azure OpenAI chat completions",
            extra={
                "provider": self.name,
                "deployment": request.model,
                "messages": len(request.messages),
                "request_id": request_id,
            },
        )

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                "Azure OpenAI request completed",
                extra={
                    "provider": self.name,
                    "deployment": request.model,
                    "latency_ms": latency_ms,
                },
            )

            data = response.json()
            return ChatCompletionResponse(**data)

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Azure OpenAI request timeout",
                extra={
                    "provider": self.name,
                    "deployment": request.model,
                    "latency_ms": latency_ms,
                },
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                logger.warning(
                    "Azure OpenAI rate limit exceeded",
                    extra={
                        "provider": self.name,
                        "deployment": request.model,
                        "retry_after": retry_seconds,
                    },
                )
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            error_detail = self._extract_error_detail(e.response)
            logger.error(
                "Azure OpenAI HTTP error",
                extra={
                    "provider": self.name,
                    "deployment": request.model,
                    "status_code": e.response.status_code,
                    "error": error_detail,
                },
            )
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def stream_chat_completion(
        self, request: ChatCompletionRequest, request_id: str | None = None
    ) -> AsyncGenerator[ChatCompletionStreamChunk, None]:
        """
        Execute streaming chat completion via Azure.

        Args:
            request: OpenAI-compatible request with stream=true
            request_id: Optional request ID for tracing

        Yields:
            ChatCompletionStreamChunk: Stream chunks with deltas

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Azure
            ProviderRateLimitError: Rate limit exceeded
        """
        start_time = time.time()

        # Build Azure-specific URL
        url = self._build_deployment_url(request.model, "chat/completions")

        # Build request payload
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        payload.pop("model", None)  # Remove model (it's in URL)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Starting Azure OpenAI streaming",
            extra={
                "provider": self.name,
                "deployment": request.model,
                "request_id": request_id,
            },
        )

        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()

                chunk_count = 0
                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str.strip() == "[DONE]":
                            latency_ms = int((time.time() - start_time) * 1000)
                            logger.debug(
                                "Azure OpenAI streaming completed",
                                extra={
                                    "provider": self.name,
                                    "deployment": request.model,
                                    "chunks": chunk_count,
                                    "latency_ms": latency_ms,
                                },
                            )
                            break

                        try:
                            import json

                            data = json.loads(data_str)
                            chunk = ChatCompletionStreamChunk(**data)
                            chunk_count += 1
                            yield chunk

                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            logger.warning(
                "Azure OpenAI streaming timeout",
                extra={"provider": self.name, "deployment": request.model},
            )
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            error_detail = self._extract_error_detail(e.response)
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def create_embeddings(
        self, request: EmbeddingRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate embeddings via Azure OpenAI.

        Args:
            request: Embedding request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible embedding response

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Azure
            ProviderRateLimitError: Rate limit exceeded
        """
        start_time = time.time()

        # Build Azure-specific URL
        url = self._build_deployment_url(request.model, "embeddings")

        # Build request payload
        payload = request.model_dump(exclude_none=True)
        payload.pop("model", None)  # Remove model (it's in URL)

        # Add request headers
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        logger.debug(
            "Calling Azure OpenAI embeddings",
            extra={
                "provider": self.name,
                "deployment": request.model,
                "request_id": request_id,
            },
        )

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            data: dict[str, Any] = response.json()

            logger.debug(
                "Azure OpenAI embeddings completed",
                extra={
                    "provider": self.name,
                    "deployment": request.model,
                    "latency_ms": latency_ms,
                },
            )

            return data

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(self.name, self.timeout) from e

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else None
                raise ProviderRateLimitError(self.name, retry_seconds) from e

            error_detail = self._extract_error_detail(e.response)
            raise ProviderHTTPError(self.name, e.response.status_code, error_detail) from e

    async def create_response(
        self, request: ResponseRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Create stateful response via Azure OpenAI.

        Azure doesn't natively support /v1/responses.
        LiteLLM provides translation.

        Args:
            request: Response request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response

        Raises:
            ProviderHTTPError: Not supported by Azure (501)
        """
        logger.warning(
            "Azure OpenAI /v1/responses not natively supported",
            extra={"provider": self.name, "deployment": request.model},
        )

        # If using via LiteLLM, it handles translation
        # Direct Azure calls would need custom implementation
        raise ProviderHTTPError(
            self.name, 501, "Azure OpenAI does not support /v1/responses natively"
        )

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract error detail from Azure error response."""
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
        Check Azure OpenAI provider health.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Simple GET to base URL
            response = await self.client.get(f"/openai?api-version={self.api_version}", timeout=5.0)
            response.raise_for_status()
            logger.debug(f"Azure provider {self.name} health check: OK")
            return True
        except Exception as e:
            logger.warning(
                f"Azure provider {self.name} health check failed",
                extra={"error": str(e)},
            )
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "AzureOpenAIProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
