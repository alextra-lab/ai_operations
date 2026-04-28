"""
Base provider protocol and configuration.

Defines the interface that all provider adapters must implement.
Follows ADR-050 (Inference Gateway) and ADR-052 (Provider Routing).
"""

from typing import Any, AsyncIterator, Callable, Protocol, TypeVar

import backoff
import httpx
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from shared.providers import ProviderConfig  # type: ignore[import-untyped]

from ..utils.errors import ProviderHTTPError, ProviderTimeoutError

logger = configure_logging(service_name="provider_base")

# Type variable for return values
T = TypeVar("T")


class BaseProvider:
    """
    Base provider class with retry logic and error handling.

    Provides common functionality for all provider adapters:
    - Retry logic with exponential backoff (2 attempts)
    - Error handling and logging
    - Context manager support for httpx client cleanup

    Follows ADR-054 (Error Taxonomy) and ADR-050 (Inference Gateway).

    Example:
        class MyProvider(BaseProvider):
            async def chat_completion(self, request, request_id=None):
                return await self.call_with_retry(
                    self._do_chat_completion,
                    request,
                    request_id
                )

            async def _do_chat_completion(self, request, request_id):
                # Actual API call here
                pass
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize base provider.

        Args:
            config: Provider configuration from database
        """
        self.name = config.name
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.timeout = float(config.timeout_seconds) if config.timeout_seconds else 30.0
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseProvider":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup httpx client."""
        if self.client:
            await self.client.aclose()

    async def call_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Call provider function with retry logic and circuit breaker protection.

        Retries on transient errors (Timeout, ConnectionError) with
        exponential backoff. Max 2 attempts total.

        Circuit breaker protection:
        - Fast-fails if circuit OPEN (provider unhealthy)
        - Records success/failure for circuit state management
        - Automatic recovery testing

        Args:
            func: Async function to call
            *args: Positional arguments to func
            **kwargs: Keyword arguments to func

        Returns:
            Result from func

        Raises:
            CircuitOpenError: If circuit breaker is OPEN
            ProviderTimeoutError: After all retries exhausted
            ProviderHTTPError: HTTP error from provider
            Exception: Other unexpected errors

        Note:
            - Max tries: 2 (initial + 1 retry)
            - Max backoff: 10 seconds
            - Only retries: Timeout, ConnectionError
            - Circuit breaker: 3 failures → OPEN for 60s
        """
        # Import circuit breaker here to avoid circular import
        from ..services.circuit_breaker import get_circuit_breaker

        circuit_breaker = get_circuit_breaker()

        @backoff.on_exception(
            backoff.expo,
            (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError),
            max_tries=2,  # Total: 2 attempts (initial + 1 retry)
            max_value=10,  # Max backoff: 10 seconds
            on_backoff=lambda details: logger.warning(
                "Provider retry attempt",
                extra={
                    "provider": self.name,
                    "attempt": details.get("tries", 0),
                    "wait_seconds": round(details.get("wait", 0), 2),
                    "exception": str(details.get("exception", "")),
                },
            ),
        )
        async def _call_with_backoff() -> Any:
            result = func(*args, **kwargs)
            # Handle both sync and async functions
            if hasattr(result, "__await__"):
                return await result  # type: ignore[misc]
            return result  # type: ignore[return-value]

        # Execute with circuit breaker protection
        async def _execute() -> Any:
            try:
                result = await _call_with_backoff()
                return result
            except httpx.TimeoutException as e:
                # Convert httpx timeout to ProviderTimeoutError after retries exhausted
                raise ProviderTimeoutError(
                    provider_name=self.name,
                    timeout_seconds=self.timeout,
                ) from e
            except httpx.HTTPStatusError as e:
                # Convert to ProviderHTTPError (no retry)
                raise ProviderHTTPError(
                    provider_name=self.name,
                    status_code=e.response.status_code,
                    detail=e.response.text[:200],  # Limit detail length
                ) from e

        # Call through circuit breaker (records success/failure)
        result = await circuit_breaker.call(self.name, _execute)
        return result  # type: ignore[return-value]  # Circuit breaker call preserves type

    async def health_check(self) -> bool:
        """
        Default health check implementation.

        Returns:
            True (override in subclass for actual health check)
        """
        return True


class Provider(Protocol):
    """
    Provider protocol - all provider adapters must implement this interface.

    Follows ADR-050 (dumb pipe v1) and ADR-052 (simple routing).

    Note: Import ChatCompletionRequest/Response from app.models
    """

    name: str
    config: ProviderConfig

    async def chat_completion(self, request: Any, request_id: str | None = None) -> Any:
        """
        Execute synchronous chat completion.

        Args:
            request: ChatCompletionRequest (OpenAI-compatible)
            request_id: Optional request ID for tracing

        Returns:
            ChatCompletionResponse (OpenAI-compatible)

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from provider
            ProviderRateLimitError: Rate limit exceeded
        """
        ...

    async def chat_completion_stream(
        self, request: Any, request_id: str | None = None
    ) -> AsyncIterator[str]:
        """
        Execute streaming chat completion.

        Args:
            request: ChatCompletionRequest with stream=True
            request_id: Optional request ID for tracing

        Yields:
            SSE-formatted chunks: "data: {json}\\n\\n"

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from provider
            ProviderRateLimitError: Rate limit exceeded
        """
        ...

    async def health_check(self) -> bool:
        """
        Check provider health.

        Returns:
            True if provider is healthy, False otherwise
        """
        ...
