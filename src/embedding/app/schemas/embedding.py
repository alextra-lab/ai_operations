"""
Pydantic schemas for embedding API requests and responses, including OpenAI-compatible formats.
"""

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator

from shared.logging_utils.fastapi import configure_logging

# Configure centralized logger for this router
logger = configure_logging(service_name="embedding_schemas")


# === Internal Embedding API Schemas ===


class ModelType(str, Enum):
    OPENAI = "openai"
    LOCAL = "local"
    # Add other model types as needed

    def __str__(self) -> str:
        return str(self.value)


class EmbeddingRequest(BaseModel):
    texts: Annotated[list[str], Field(min_length=1, description="List of texts to embed")]
    model: str | ModelType | None = Field(
        None, description="Model name to use (can be ModelType enum or specific model name string)"
    )
    user: str | None = Field(None, description="User identifier for tracking")

    @field_validator("texts", mode="before")
    def validate_texts(cls, texts: Any) -> Any:
        for i, text in enumerate(texts):
            if not text.strip():
                raise ValueError(f"Text at index {i} is empty")
            if len(text) > 32000:
                raise ValueError(f"Text at index {i} exceeds maximum length")
        return texts


class EmbeddingResponse(BaseModel):
    vectors: list[list[float]] = Field(..., description="Embedding vectors for each input text")
    model: str = Field(..., description="Model used to generate embeddings")
    dimensions: int = Field(..., description="Dimension of embedding vectors")
    processing_time: float = Field(
        ..., description="Time taken to process the embedding request (seconds)"
    )
    usage: dict[str, Any] | None = Field(None, description="Usage metadata (e.g., token counts)")

    model_config = {"frozen": True}


class AdminConfigReloadResponse(BaseModel):
    success: bool = Field(..., description="Whether the configuration reload was successful")
    message: str = Field(..., description="Status message about the reload operation")
    providers: dict[str, Any] = Field(
        ...,
        description="Mapping of provider names to their initialization status, health, and models",
    )

    model_config = {"frozen": True}


# === OpenAI-Compatible Schemas ===


class OpenAIEmbeddingData(BaseModel):
    embedding: list[float] = Field(..., description="The embedding vector")
    index: int = Field(..., description="Index of the embedding in the list")
    object: str = Field(default="embedding", description="Object type (always 'embedding')")

    model_config = {"frozen": True}


class OpenAIUsage(BaseModel):
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    total_tokens: int = Field(..., description="Total number of tokens processed")

    model_config = {"frozen": True}


class OpenAIEmbeddingRequest(BaseModel):
    input: str | Annotated[list[str], Field(min_length=1)] = Field(
        ..., description="Input text(s) to embed"
    )
    model: str | ModelType | None = Field(
        None,
        description="Model name to use (can be ModelType enum, provider name, or specific model name string)",
    )
    encoding_format: str | None = Field("float", description="The format of the output embeddings")
    user: str | None = Field(None, description="User identifier for tracking")


class OpenAIEmbeddingResponse(BaseModel):
    data: list[OpenAIEmbeddingData]
    model: str
    usage: OpenAIUsage
    object: str = Field(default="list", description="Object type (always 'list')")

    model_config = {"frozen": True}
