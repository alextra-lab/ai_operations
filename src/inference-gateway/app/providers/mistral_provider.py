"""
Mistral AI provider adapter.

Mistral Cloud API is largely OpenAI-compatible with minor differences.
Extends OpenAIProvider with Mistral-specific handling.

Key differences:
- Different model naming (mistral-tiny, mistral-small, mistral-medium, etc.)
- Slightly different error responses
- Native support for embeddings via mistral-embed
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..models.embedding_request import EmbeddingRequest
from ..models.response_request import ResponseRequest
from ..providers.openai_provider import OpenAIProvider

logger = configure_logging(service_name="mistral_provider")


class MistralProvider(OpenAIProvider):
    """
    Mistral AI API client.

    Extends OpenAIProvider since Mistral API is OpenAI-compatible.
    Minor differences handled via inheritance overrides.

    Supported endpoints:
    - POST /v1/chat/completions (sync + streaming)
    - POST /v1/embeddings (mistral-embed model)
    - POST /v1/responses (via LiteLLM translation)
    """

    def __init__(self, config):
        """
        Initialize Mistral provider.

        Args:
            config: Provider configuration from database
        """
        super().__init__(config)
        logger.debug(
            "Initialized Mistral provider",
            extra={
                "provider_name": self.name,
                "base_url": self.base_url,
            },
        )

    async def create_embeddings(
        self, request: EmbeddingRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate embeddings via Mistral API.

        Mistral embeddings API is OpenAI-compatible.
        Uses mistral-embed model.

        Args:
            request: Embedding request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible embedding response

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Mistral
            ProviderRateLimitError: Rate limit exceeded
        """
        logger.debug(
            "Mistral embeddings request",
            extra={
                "provider": self.name,
                "model": request.model,
                "request_id": request_id,
            },
        )

        # Mistral embeddings API is OpenAI-compatible
        return await super().create_embeddings(request, request_id)

    async def create_response(
        self, request: ResponseRequest, request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Create stateful response via Mistral API.

        Mistral doesn't natively support /v1/responses.
        LiteLLM provides translation from OpenAI format.

        Args:
            request: Response request
            request_id: Optional request ID for tracing

        Returns:
            OpenAI-compatible response

        Raises:
            ProviderTimeoutError: Request timeout
            ProviderHTTPError: HTTP error from Mistral
            ProviderRateLimitError: Rate limit exceeded
        """
        logger.debug(
            "Mistral responses request (via LiteLLM translation)",
            extra={
                "provider": self.name,
                "model": request.model,
                "request_id": request_id,
            },
        )

        # LiteLLM handles translation to Mistral's native format
        return await super().create_response(request, request_id)

    async def health_check(self) -> bool:
        """
        Check Mistral provider health.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Use /v1/models endpoint for health check
            if self.client is None:
                return False
            response = await self.client.get("/models", timeout=5.0)
            response.raise_for_status()
            logger.debug(f"Mistral provider {self.name} health check: OK")
            return True
        except Exception as e:
            logger.warning(
                f"Mistral provider {self.name} health check failed",
                extra={"error": str(e)},
            )
            return False
