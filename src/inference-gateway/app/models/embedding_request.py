"""
Embedding request models for OpenAI-compatible embeddings endpoint.

Supports /v1/embeddings endpoint for:
- Document ingestion (RAG)
- Semantic search
- Similarity scoring
"""

from typing import Union

from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    """
    OpenAI-compatible embeddings request.

    Used for generating vector embeddings from text input.
    Critical for RAG functionality in AI Operations Platform (AIOP).

    Attributes:
        model: Model ID (e.g., 'bge-embeddings', 'text-embedding-3-small')
        input: Single string or list of strings to embed
        encoding_format: Output format ('float' or 'base64')
        dimensions: Optional output dimensions (for models that support it)
        user: Optional user ID for tracking and rate limiting
    """

    model: str = Field(
        ...,
        description="Model ID to use for embeddings",
        examples=["bge-embeddings", "text-embedding-3-small"],
    )

    input: Union[str, list[str]] = Field(
        ...,
        description="Text(s) to embed. Single string or array of strings.",
        examples=["What is cybersecurity?", ["Doc 1", "Doc 2", "Doc 3"]],
    )

    encoding_format: str = Field(
        default="float",
        description="Format for embeddings output",
        pattern="^(float|base64)$",
    )

    dimensions: int | None = Field(
        default=None,
        description="Number of dimensions for output (if model supports)",
        gt=0,
    )

    user: str | None = Field(
        default=None, description="End-user ID for tracking and abuse prevention"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "model": "bge-embeddings",
                "input": "What is a cybersecurity threat?",
                "encoding_format": "float",
            }
        }
