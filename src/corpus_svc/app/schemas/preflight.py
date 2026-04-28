"""
Preflight analysis schemas for corpus management.

Supports intelligent chunking strategy recommendation based on document structure.
ADR-034: Use Case Validation & Test Harness
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .chunking_enums import ChunkingStrategy


class StructureSignals(BaseModel):
    """Document structure analysis signals."""

    heading_density: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of heading lines to total lines"
    )
    table_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of table content to total content"
    )
    list_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of list items to total lines")
    avg_paragraph_length: float = Field(
        ..., ge=0.0, description="Average paragraph length in tokens"
    )
    sentence_count: int = Field(..., ge=0, description="Total sentence count in sample")
    token_count: int = Field(..., ge=0, description="Total token count in sample")
    has_code_blocks: bool = Field(False, description="Whether document contains code blocks")
    has_equations: bool = Field(False, description="Whether document contains equations")
    ocr_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="OCR confidence score if applicable"
    )


class StrategyBenchmarkResult(BaseModel):
    """Benchmark result for a single chunking strategy."""

    strategy: ChunkingStrategy
    chunk_count: int = Field(..., ge=0, description="Number of chunks created")
    avg_chunk_size: float = Field(..., ge=0.0, description="Average chunk size in tokens")
    std_chunk_size: float = Field(..., ge=0.0, description="Standard deviation of chunk sizes")
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")

    # Retrieval metrics (if test suite provided)
    hit_at_k: float | None = Field(None, ge=0.0, le=1.0, description="Hit@K metric")
    mrr: float | None = Field(None, ge=0.0, le=1.0, description="Mean Reciprocal Rank")
    ndcg: float | None = Field(None, ge=0.0, le=1.0, description="Normalized DCG@K")
    zero_result_rate: float | None = Field(None, ge=0.0, le=1.0, description="Zero result rate")

    # Scoring
    score: float = Field(..., ge=0.0, le=1.0, description="Overall strategy score (0.0-1.0)")
    rank: int | None = Field(None, ge=1, description="Rank among all strategies tested")


class PreflightRecommendation(BaseModel):
    """Recommended chunking strategy with reasoning."""

    strategy: ChunkingStrategy
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in recommendation (0.0-1.0)"
    )
    reasoning: list[str] = Field(..., description="Human-readable reasoning for recommendation")
    alternative_strategies: list[ChunkingStrategy] = Field(
        default_factory=list,
        description="Alternative strategies if user wants to override",
    )


class PreflightReport(BaseModel):
    """Complete preflight analysis report."""

    document_id: UUID | None = Field(None, description="Document ID if available")
    document_name: str = Field(..., description="Document filename")
    document_type: str = Field(..., description="Document MIME type")
    document_size_bytes: int = Field(..., ge=0, description="Document size in bytes")
    sample_size_tokens: int = Field(..., ge=0, description="Sample size analyzed (tokens)")

    structure_signals: StructureSignals
    strategy_results: list[StrategyBenchmarkResult]
    recommendation: PreflightRecommendation

    test_suite_id: UUID | None = Field(None, description="Test suite used for benchmarking")
    analysis_time_ms: int = Field(..., ge=0, description="Total analysis time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class PreflightRequest(BaseModel):
    """Request schema for preflight analysis."""

    test_suite_id: UUID | None = Field(
        None, description="Test suite ID for retrieval metrics (optional)"
    )
    strategies_to_test: list[ChunkingStrategy] | None = Field(
        None,
        description="Specific strategies to test (defaults to all core strategies)",
    )
    max_sample_tokens: int = Field(
        default=10000,
        ge=1000,
        le=50000,
        description="Maximum sample size in tokens for analysis",
    )
    include_retrieval_metrics: bool = Field(
        default=True,
        description="Whether to run retrieval metrics (requires test_suite_id)",
    )


class PreflightAcceptRequest(BaseModel):
    """Request schema for accepting preflight recommendation."""

    preflight_report_id: UUID = Field(..., description="Preflight report ID")
    strategy: ChunkingStrategy = Field(..., description="Selected chunking strategy")
    override_reasoning: str | None = Field(
        None, description="Reasoning if overriding recommendation"
    )


class PreflightAcceptResponse(BaseModel):
    """Response schema for accepting preflight recommendation."""

    accepted: bool
    strategy: ChunkingStrategy
    collection_id: UUID = Field(..., description="Collection ID where document will be ingested")
    message: str


class ChunkingConfigOverride(BaseModel):
    """Expert mode: override chunking configuration parameters."""

    strategy: ChunkingStrategy
    chunk_size: int | None = Field(
        None,
        ge=128,
        le=8192,
        description="Chunk size in tokens (must not exceed embedding model context window)",
    )
    overlap: int | None = Field(None, ge=0, le=1024, description="Overlap size in tokens")

    # Strategy-specific overrides
    heading_levels: list[int] | None = Field(
        None, description="[heading_aware] Heading levels to split on (e.g., [1,2,3])"
    )
    min_chunk_size: int | None = Field(None, ge=64, le=2048, description="Minimum chunk size")
    max_chunk_size: int | None = Field(
        None,
        ge=256,
        le=8192,
        description="Maximum chunk size in tokens (must not exceed embedding model context window)",
    )

    metadata: dict[str, Any] | None = Field(
        None, description="Additional strategy-specific parameters"
    )
