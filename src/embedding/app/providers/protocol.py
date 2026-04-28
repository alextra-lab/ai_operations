"""
Protocol definitions for embedding providers.
"""

from typing import Protocol, runtime_checkable

from shared.logging_utils.fastapi import configure_logging

# Use relative imports
from ..schemas.embedding import EmbeddingRequest, EmbeddingResponse
from ..types import ProviderType

# Configure logger for this protocol module
logger = configure_logging(service_name="provider_protocol")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol defining the interface for embedding providers.

    All embedding providers must implement this interface.
    """

    name: str
    provider_type: ProviderType
    priority: int

    async def health_check(self) -> dict[str, bool]:
        """
        Check the health of this provider.

        Returns:
            dict: Health status information with component checks
        """
        ...

    async def get_model_info(self) -> dict[str, dict]:
        """
        Get information about available models.

        Returns:
            dict: Dictionary mapping model names to their metadata
        """
        ...

    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for the provided texts.

        Args:
            request: EmbeddingRequest object containing texts to embed

        Returns:
            EmbeddingResponse: Response containing embedding vectors

        Raises:
            ValueError: If the texts are invalid
            RuntimeError: If embedding generation fails
        """
        ...


class ModelNotFoundError(Exception):
    """Raised when a requested model cannot be found."""

    def __init__(self, message: str):
        logger.error(f"ModelNotFoundError: {message}")
        super().__init__(message)


class ProviderNotAvailableError(Exception):
    """Raised when a provider is not available."""

    def __init__(self, message: str):
        logger.error(f"ProviderNotAvailableError: {message}")
        super().__init__(message)


class EmbeddingError(Exception):
    """Base class for embedding-related errors."""

    def __init__(self, message: str):
        logger.error(f"EmbeddingError: {message}")
        super().__init__(message)
