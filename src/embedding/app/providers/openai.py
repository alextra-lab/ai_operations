"""
OpenAI-compatible embedding provider implementation.
"""

import time
from typing import Any

import httpx
from openai import (
    OpenAI,
    OpenAIError,  # For specific exception handling
)

from shared.config.secrets import resolve_secret
from shared.logging_utils.fastapi import configure_logging

from ..config.models import ModelConfig, OpenAIConnectionConfig
from ..providers.protocol import ModelNotFoundError
from ..schemas.embedding import EmbeddingRequest, EmbeddingResponse
from ..types import ProviderType

# Configure centralized logger for this provider
logger = configure_logging(service_name="openai_provider")

# Health check cache TTL (in seconds) - prevents excessive provider pings
HEALTH_CHECK_CACHE_TTL = 60  # Cache health check results for 60 seconds


class OpenAIProvider:
    """
    Implementation of EmbeddingProvider for OpenAI-compatible endpoints.

    This provider connects to local OpenAI-compatible servers for embedding generation.
    """

    def __init__(
        self,
        name: str,
        connection_config: OpenAIConnectionConfig,
        models: list[ModelConfig],
        priority: int = 10,
        api_key: str | None = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            name: Provider name
            connection_config: Configuration for OpenAI-compatible server connection
            models: List of models available through this provider
            priority: Provider priority (lower is higher priority)
        """
        self.name = name
        self.provider_type = ProviderType.OPENAI_COMPATIBLE
        self.priority = priority
        self.connection_config = connection_config
        self.models = {model.name: model for model in models}
        if not models:
            raise ValueError("No models provided to OpenAIProvider")
        self.default_model = next((model for model in models if model.default), models[0])
        self._api_key_override = api_key

        # Initialize OpenAI client (supports both OpenAI and compatible endpoints)
        self._initialize_client()

        # Health check cache to prevent excessive provider pings
        self._health_check_cache: dict[str, Any] | None = None
        self._health_check_cache_time: float = 0.0

        api_key_env = self.connection_config.api_key_env or "OPENAI_API_KEY"
        api_key_present = bool(self._api_key_override) or bool(resolve_secret(api_key_env))
        logger.info(
            "Initialized OpenAI provider %s with %d models (api_key_configured=%s)",
            name,
            len(models),
            "yes" if api_key_present else "no",
        )
        # Never log the actual API key value

    def _initialize_client(self) -> None:
        api_key: str | None
        if self._api_key_override:
            api_key = self._api_key_override
        else:
            api_key_env = self.connection_config.api_key_env or "OPENAI_API_KEY"
            api_key = resolve_secret(api_key_env)
        if not api_key:
            raise RuntimeError("Missing required API key for OpenAIProvider (no override provided)")
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.connection_config.url,
            timeout=self.connection_config.timeout_seconds,
            max_retries=self.connection_config.max_retries,
        )

    def reload_client(self, new_config: OpenAIConnectionConfig | None = None) -> None:
        if new_config:
            self.connection_config = new_config
        self._initialize_client()
        # Clear health check cache when client is reloaded (config may have changed)
        self._health_check_cache = None
        self._health_check_cache_time = 0.0

    async def health_check(self) -> dict[str, bool]:
        """
        Check the health of this provider using lightweight endpoint check.

        Uses cached results to prevent excessive provider pings.
        Caches results for HEALTH_CHECK_CACHE_TTL seconds.

        Returns:
            dict: Health status information with component checks
        """
        api_key_env = self.connection_config.api_key_env or "OPENAI_API_KEY"
        result = {
            "available": False,
            "api_key_configured": bool(self._api_key_override) or bool(resolve_secret(api_key_env)),
            "connection": False,
        }

        # Check cache first to avoid excessive pings
        current_time = time.time()
        if (
            self._health_check_cache is not None
            and (current_time - self._health_check_cache_time) < HEALTH_CHECK_CACHE_TTL
        ):
            logger.debug(f"Returning cached health check result for provider {self.name}")
            return self._health_check_cache

        try:
            # Use lightweight /models endpoint check instead of full embedding request
            # This is much faster and less resource-intensive than sending an embedding request
            # Most OpenAI-compatible APIs support GET /v1/models endpoint
            base_url = self.connection_config.url.rstrip("/")
            # Handle case where base_url already includes /v1 (e.g., http://localhost:8000/v1)
            # If URL ends with /v1, just append /models; otherwise add /v1/models
            if base_url.endswith("/v1"):
                models_url = f"{base_url}/models"
            else:
                models_url = f"{base_url}/v1/models"
            headers = {}

            # Add API key if configured
            api_key = self._api_key_override or resolve_secret(api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Use short timeout for health checks
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(models_url, headers=headers)
                response.raise_for_status()

            # If we got a successful response, the connection is working
            result["connection"] = True
            result["available"] = True

            # Cache the successful result
            self._health_check_cache = result
            self._health_check_cache_time = current_time

            logger.debug(
                f"Health check successful for provider {self.name} (using /v1/models endpoint)"
            )
            return result

        except Exception as e:
            logger.debug(
                f"Health check failed for OpenAI provider {self.name}: {e!s}",
                exc_info=False,  # Don't log full trace for expected health check failures
            )
            # Cache failed result too, but with shorter TTL implied by normal cache expiry
            self._health_check_cache = result
            self._health_check_cache_time = current_time
            return result

    async def get_model_info(self) -> dict[str, dict]:
        """
        Get information about available models.

        Returns:
            dict: Dictionary mapping model names to their metadata
        """
        info = {}
        for name, model in self.models.items():
            server_name = model.server_model_name or name
            info[name] = {
                "dimensions": model.dimensions,
                "server_model_name": server_name,
                "default": model.default,
                "batch_size": model.batch_size,
                "metadata": model.metadata or {},
            }
        return info

    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for the provided texts.

        Args:
            request: EmbeddingRequest object containing texts to embed

        Returns:
            EmbeddingResponse: Response containing embedding vectors

        Raises:
            ValueError: If the texts are invalid
            ModelNotFoundError: If the requested model cannot be found
            RuntimeError: If embedding generation fails
        """
        if (
            not request.texts
            or not isinstance(request.texts, list)
            or not all(isinstance(t, str) for t in request.texts)
        ):
            logger.error("Invalid input: `request.texts` must be a non-empty list of strings")
            raise ValueError("`request.texts` must be a non-empty list of strings")

        start_time = time.time()

        # Determine which model to use
        # Handle both ModelType enum and string model names
        if request.model is None:
            model_name = self.default_model.name
        elif isinstance(request.model, str):
            model_name = request.model
        else:
            # ModelType enum - convert to string
            model_name = (
                str(request.model.value) if hasattr(request.model, "value") else str(request.model)
            )

        if model_name not in self.models:
            logger.error(f"Model {model_name} not found in provider {self.name}")
            raise ModelNotFoundError(f"Model {model_name} not found in provider {self.name}")

        model_config = self.models[model_name]
        server_model_name = model_config.server_model_name or model_name

        # Process in batches to avoid request size limits
        batch_size = model_config.batch_size
        all_vectors = []
        total_tokens = 0

        for i in range(0, len(request.texts), batch_size):
            batch = request.texts[i : i + batch_size]
            try:
                response = await self._embed_single_batch(batch, server_model_name, request.user)
                vectors = [item["embedding"] for item in response["data"]]
                all_vectors.extend(vectors)
                total_tokens += response["usage"].get("total_tokens", 0)
            except OpenAIError as e:
                logger.error(f"OpenAI error embedding batch {i // batch_size}: {e!s}")
                raise RuntimeError(f"Failed to generate embeddings: {e!s}")

        processing_time = time.time() - start_time

        logger.info(
            f"Generated embeddings for {len(request.texts)} texts using model '{model_name}' in {processing_time:.2f}s"
        )

        dimensions = (
            model_config.dimensions
            if model_config.dimensions is not None
            else (len(all_vectors[0]) if all_vectors else 0)
        )
        return EmbeddingResponse(
            vectors=all_vectors,
            model=model_name,
            dimensions=dimensions,
            processing_time=processing_time,
            usage={"prompt_tokens": total_tokens, "total_tokens": total_tokens},
        )

    async def _embed_single_batch(
        self, texts: list[str], model_name: str, user: str | None = None
    ) -> dict[str, Any]:
        """
        Embed a batch of texts using the OpenAI embeddings endpoint.

        Args:
            texts: List of texts to embed
            model_name: Model name to use for embedding
            user: Optional user identifier

        Returns:
            dict: Raw OpenAI response as a dictionary
        """
        try:
            # Build request parameters
            params = {
                "model": model_name,
                "input": texts,
            }

            if user:
                params["user"] = user

            # Ensure that params is correctly formatted (SDK expects list of str)
            input_text = params.get("input", [])
            if not isinstance(input_text, list):
                input_text = [str(input_text)]
            # Flatten to list[str] for SDK: normalize each item to str (SDK expects list[str])
            input_list_str: list[str] = []
            for sub in input_text:
                for item in sub if isinstance(sub, list | tuple) else [sub]:
                    input_list_str.append(str(item))

            # The OpenAI Python SDK's .embeddings.create returns a pydantic model; use .model_dump() for dict
            response = self.client.embeddings.create(input=input_list_str, model=model_name)
            return response.model_dump()
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e!s}")
            raise RuntimeError(f"OpenAI API error: {e!s}")
