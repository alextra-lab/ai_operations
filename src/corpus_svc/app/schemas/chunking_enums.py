"""
Chunking Strategy Enums for Stateless Core v1

This module defines enums and schemas for document chunking strategies
used in the corpus management enhancement.

Supports 7 chunking strategies:
- 3 core strategies (always available)
- 2 expert strategies (feature-flagged)
- 2 legacy strategies (maintain compatibility)
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing."""

    # Core strategies (always available)
    FIXED_TOKEN = "fixed_token"
    SLIDING_TOKEN = "sliding_token"
    HEADING_AWARE = "heading_aware"
    SENTENCE_PARAGRAPH = "sentence_paragraph"
    TABLE_AWARE = "table_aware"

    # Expert strategies (feature-flagged)
    SEMANTIC_ADAPTIVE = "semantic_adaptive"
    PAGE_BLOCK = "page_block"

    # Legacy (maintain compatibility)
    RECURSIVE = "recursive"


class ChunkingMode(str, Enum):
    """Chunking execution modes."""

    SYNC = "sync"  # Synchronous processing
    ASYNC = "async"  # Asynchronous processing


class ChunkingConfig(BaseModel):
    """Configuration for a specific chunking strategy."""

    strategy: ChunkingStrategy = Field(..., description="The chunking strategy to use")
    chunk_size: int = Field(
        512,
        ge=64,
        le=8192,
        description="Target chunk size in tokens (must not exceed embedding model context window)",
    )
    chunk_overlap: int = Field(50, ge=0, le=200, description="Overlap between chunks in tokens")
    min_chunk_size: int = Field(64, ge=32, le=512, description="Minimum chunk size in tokens")
    max_chunk_size: int = Field(
        2048,
        ge=512,
        le=8192,
        description="Maximum chunk size in tokens (must not exceed embedding model context window)",
    )
    preserve_whitespace: bool = Field(True, description="Whether to preserve whitespace formatting")
    respect_sentence_boundaries: bool = Field(
        True, description="Whether to respect sentence boundaries"
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int) -> int:
        """Validate that overlap is reasonable."""
        if v < 0:
            raise ValueError("chunk_overlap must be non-negative")
        return v

    @field_validator("min_chunk_size")
    @classmethod
    def validate_min_size(cls, v: int) -> int:
        """Validate that min_chunk_size is reasonable."""
        if v < 1:
            raise ValueError("min_chunk_size must be at least 1")
        return v

    @field_validator("max_chunk_size")
    @classmethod
    def validate_max_size(cls, v: int) -> int:
        """Validate that max_chunk_size is reasonable."""
        if v < 1:
            raise ValueError("max_chunk_size must be at least 1")
        return v


class ChunkingResult(BaseModel):
    """Result of a chunking operation."""

    strategy: ChunkingStrategy = Field(..., description="Strategy used for chunking")
    chunks: list[str] = Field(..., description="Generated text chunks")
    chunk_count: int = Field(..., ge=0, description="Number of chunks generated")
    total_tokens: int = Field(..., ge=0, description="Total tokens across all chunks")
    avg_chunk_size: float = Field(..., ge=0.0, description="Average chunk size in tokens")
    processing_time_ms: int = Field(..., ge=0, description="Time taken to process in milliseconds")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class ChunkingAnalysis(BaseModel):
    """Analysis of chunking strategy performance."""

    strategy: ChunkingStrategy = Field(..., description="Strategy that was analyzed")
    document_id: UUID = Field(..., description="Document that was analyzed")
    chunk_count: int = Field(..., ge=0, description="Number of chunks generated")
    avg_chunk_size: float = Field(..., ge=0.0, description="Average chunk size in tokens")
    size_variance: float = Field(..., ge=0.0, description="Variance in chunk sizes")
    overlap_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of overlap to chunk size")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )


class ChunkingComparison(BaseModel):
    """Comparison of multiple chunking strategies."""

    document_id: UUID = Field(..., description="Document that was compared")
    strategies: list[ChunkingStrategy] = Field(..., description="Strategies that were compared")
    results: list[ChunkingResult] = Field(..., description="Results for each strategy")
    best_strategy: ChunkingStrategy = Field(..., description="Recommended strategy")
    best_score: float = Field(..., ge=0.0, le=1.0, description="Score of the best strategy")
    comparison_metadata: dict[str, str] = Field(
        default_factory=dict, description="Comparison metadata"
    )


class ChunkingPreflightRequest(BaseModel):
    """Request for chunking preflight analysis."""

    document_id: UUID = Field(..., description="Document to analyze")
    strategies: list[ChunkingStrategy] = Field(..., description="Strategies to test")
    sample_size: int = Field(1000, ge=100, le=10000, description="Sample size for analysis")
    include_quality_metrics: bool = Field(True, description="Whether to include quality metrics")
    include_recommendations: bool = Field(True, description="Whether to include recommendations")


class ChunkingPreflightResponse(BaseModel):
    """Response from chunking preflight analysis."""

    document_id: UUID = Field(..., description="Document that was analyzed")
    recommended_strategy: ChunkingStrategy = Field(..., description="Recommended strategy")
    strategy_scores: dict[ChunkingStrategy, float] = Field(
        ..., description="Scores for each strategy"
    )
    analysis_results: list[ChunkingAnalysis] = Field(..., description="Detailed analysis results")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    recommendations: list[str] = Field(default_factory=list, description="General recommendations")


class ChunkingFeatureFlags(BaseModel):
    """Feature flags for chunking capabilities."""

    enable_expert_chunking: bool = Field(False, description="Enable expert chunking strategies")
    enable_semantic_adaptive: bool = Field(False, description="Enable semantic adaptive chunking")
    enable_page_block: bool = Field(False, description="Enable page block chunking")
    enable_preflight_analysis: bool = Field(True, description="Enable preflight analysis")
    enable_quality_metrics: bool = Field(True, description="Enable quality metrics")
    max_concurrent_chunking: int = Field(
        3, ge=1, le=10, description="Max concurrent chunking operations"
    )
