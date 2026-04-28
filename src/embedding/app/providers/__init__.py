"""
Provider implementations for embedding generation.
"""

# Use relative imports to avoid path issues when running tests
from .factory import factory as provider_factory
from .protocol import (
    EmbeddingError,
    EmbeddingProvider,
    ModelNotFoundError,
    ProviderNotAvailableError,
    ProviderType,
)

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "ModelNotFoundError",
    "ProviderNotAvailableError",
    "ProviderType",
    "provider_factory",
]
