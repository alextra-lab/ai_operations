"""
Embedding response models for OpenAI-compatible embeddings endpoint.

Follows OpenAI API response format for embeddings.
"""

from typing import List

from pydantic import BaseModel, Field


class EmbeddingData(BaseModel):
    """
    Single embedding result.

    Attributes:
        object: Always "embedding"
        embedding: Vector representation as list of floats
        index: Position in the input array (0-indexed)
    """

    object: str = Field(default="embedding", description="Object type")

    embedding: List[float] = Field(..., description="Embedding vector (array of floats)")

    index: int = Field(..., description="Index of this embedding in the input array", ge=0)


class EmbeddingUsage(BaseModel):
    """
    Token usage information.

    Attributes:
        prompt_tokens: Number of tokens in the input
        total_tokens: Total tokens used (same as prompt_tokens for embeddings)
    """

    prompt_tokens: int = Field(..., description="Number of tokens in the input", ge=0)

    total_tokens: int = Field(..., description="Total tokens used", ge=0)


class EmbeddingResponse(BaseModel):
    """
    OpenAI-compatible embeddings response.

    Returned by /v1/embeddings endpoint.

    Attributes:
        object: Always "list"
        data: Array of embedding results
        model: Model ID used to generate embeddings
        usage: Token usage information
    """

    object: str = Field(default="list", description="Object type")

    data: List[EmbeddingData] = Field(..., description="Array of embedding results")

    model: str = Field(..., description="Model ID used")

    usage: EmbeddingUsage = Field(..., description="Token usage information")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "object": "list",
                "data": [
                    {
                        "object": "embedding",
                        "embedding": [0.123, -0.456, 0.789],
                        "index": 0,
                    }
                ],
                "model": "bge-embeddings",
                "usage": {"prompt_tokens": 8, "total_tokens": 8},
            }
        }
