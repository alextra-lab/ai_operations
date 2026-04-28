"""
Schema models for the embedding service.
"""

# Use relative imports instead of absolute
from .embedding import (
    AdminConfigReloadResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelType,
    OpenAIEmbeddingData,
    OpenAIEmbeddingRequest,
    OpenAIEmbeddingResponse,
    OpenAIUsage,
)

__all__ = [
    "AdminConfigReloadResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "ModelType",
    "OpenAIEmbeddingData",
    "OpenAIEmbeddingRequest",
    "OpenAIEmbeddingResponse",
    "OpenAIUsage",
]
