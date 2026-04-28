"""Unit tests for chunking enum schemas."""

from uuid import uuid4

import pytest
from app.schemas.chunking_enums import (
    ChunkingAnalysis,
    ChunkingComparison,
    ChunkingConfig,
    ChunkingFeatureFlags,
    ChunkingMode,
    ChunkingPreflightRequest,
    ChunkingPreflightResponse,
    ChunkingResult,
    ChunkingStrategy,
)
from pydantic import ValidationError


class TestChunkingStrategy:
    """Test ChunkingStrategy enum."""

    def test_strategy_values(self) -> None:
        """Test that ChunkingStrategy has correct values."""
        assert ChunkingStrategy.FIXED_TOKEN == "fixed_token"
        assert ChunkingStrategy.SLIDING_TOKEN == "sliding_token"
        assert ChunkingStrategy.HEADING_AWARE == "heading_aware"
        assert ChunkingStrategy.SENTENCE_PARAGRAPH == "sentence_paragraph"
        assert ChunkingStrategy.TABLE_AWARE == "table_aware"
        assert ChunkingStrategy.SEMANTIC_ADAPTIVE == "semantic_adaptive"
        assert ChunkingStrategy.PAGE_BLOCK == "page_block"
        assert ChunkingStrategy.RECURSIVE == "recursive"


class TestChunkingMode:
    """Test ChunkingMode enum."""

    def test_mode_values(self) -> None:
        """Test that ChunkingMode has correct values."""
        assert ChunkingMode.SYNC == "sync"
        assert ChunkingMode.ASYNC == "async"


class TestChunkingConfig:
    """Test ChunkingConfig schema."""

    def test_valid_config(self) -> None:
        """Test creating a valid chunking config."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=64,
            max_chunk_size=1024,
            preserve_whitespace=True,
            respect_sentence_boundaries=True,
        )

        assert config.strategy == ChunkingStrategy.FIXED_TOKEN
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 64
        assert config.max_chunk_size == 1024
        assert config.preserve_whitespace is True
        assert config.respect_sentence_boundaries is True

    def test_default_values(self) -> None:
        """Test default values."""
        config = ChunkingConfig(strategy=ChunkingStrategy.FIXED_TOKEN)

        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 64
        assert config.max_chunk_size == 2048
        assert config.preserve_whitespace is True
        assert config.respect_sentence_boundaries is True

    def test_overlap_validation(self) -> None:
        """Test that overlap validation works."""
        with pytest.raises(ValidationError):
            ChunkingConfig(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_size=512,
                chunk_overlap=600,  # > chunk_size
            )

    def test_min_size_validation(self) -> None:
        """Test that min_chunk_size validation works."""
        with pytest.raises(ValidationError):
            ChunkingConfig(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_size=512,
                min_chunk_size=600,  # > chunk_size
            )

    def test_max_size_validation(self) -> None:
        """Test that max_chunk_size validation works."""
        with pytest.raises(ValidationError):
            ChunkingConfig(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_size=512,
                max_chunk_size=400,  # < chunk_size
            )

    def test_size_bounds_validation(self) -> None:
        """Test that size bounds validation works."""
        with pytest.raises(ValueError):
            ChunkingConfig(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_size=32,  # < 64 (min)
            )

        with pytest.raises(ValueError):
            ChunkingConfig(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_size=10000,  # > 2048 (max)
            )


class TestChunkingResult:
    """Test ChunkingResult schema."""

    def test_valid_result(self) -> None:
        """Test creating a valid chunking result."""
        result = ChunkingResult(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunks=["chunk1", "chunk2", "chunk3"],
            chunk_count=3,
            total_tokens=1500,
            avg_chunk_size=500.0,
            processing_time_ms=100,
            metadata={"key": "value"},
        )

        assert result.strategy == ChunkingStrategy.FIXED_TOKEN
        assert result.chunks == ["chunk1", "chunk2", "chunk3"]
        assert result.chunk_count == 3
        assert result.total_tokens == 1500
        assert result.avg_chunk_size == 500.0
        assert result.processing_time_ms == 100
        assert result.metadata == {"key": "value"}

    def test_default_metadata(self) -> None:
        """Test default metadata."""
        result = ChunkingResult(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunks=["chunk1"],
            chunk_count=1,
            total_tokens=100,
            avg_chunk_size=100.0,
            processing_time_ms=50,
        )

        assert result.metadata == {}


class TestChunkingAnalysis:
    """Test ChunkingAnalysis schema."""

    def test_valid_analysis(self) -> None:
        """Test creating a valid chunking analysis."""
        doc_id = uuid4()
        analysis = ChunkingAnalysis(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            document_id=doc_id,
            chunk_count=10,
            avg_chunk_size=512.0,
            size_variance=25.5,
            overlap_ratio=0.1,
            quality_score=0.95,
            recommendations=["Use smaller chunks", "Increase overlap"],
        )

        assert analysis.strategy == ChunkingStrategy.FIXED_TOKEN
        assert analysis.document_id == doc_id
        assert analysis.chunk_count == 10
        assert analysis.avg_chunk_size == 512.0
        assert analysis.size_variance == 25.5
        assert analysis.overlap_ratio == 0.1
        assert analysis.quality_score == 0.95
        assert analysis.recommendations == ["Use smaller chunks", "Increase overlap"]

    def test_default_recommendations(self) -> None:
        """Test default recommendations."""
        doc_id = uuid4()
        analysis = ChunkingAnalysis(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            document_id=doc_id,
            chunk_count=5,
            avg_chunk_size=400.0,
            size_variance=20.0,
            overlap_ratio=0.2,
            quality_score=0.8,
        )

        assert analysis.recommendations == []


class TestChunkingComparison:
    """Test ChunkingComparison schema."""

    def test_valid_comparison(self) -> None:
        """Test creating a valid chunking comparison."""
        doc_id = uuid4()
        result1 = ChunkingResult(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunks=["chunk1"],
            chunk_count=1,
            total_tokens=100,
            avg_chunk_size=100.0,
            processing_time_ms=50,
        )
        result2 = ChunkingResult(
            strategy=ChunkingStrategy.SLIDING_TOKEN,
            chunks=["chunk1", "chunk2"],
            chunk_count=2,
            total_tokens=200,
            avg_chunk_size=100.0,
            processing_time_ms=75,
        )

        comparison = ChunkingComparison(
            document_id=doc_id,
            strategies=[ChunkingStrategy.FIXED_TOKEN, ChunkingStrategy.SLIDING_TOKEN],
            results=[result1, result2],
            best_strategy=ChunkingStrategy.SLIDING_TOKEN,
            best_score=0.95,
            comparison_metadata={"test": "data"},
        )

        assert comparison.document_id == doc_id
        assert len(comparison.strategies) == 2
        assert len(comparison.results) == 2
        assert comparison.best_strategy == ChunkingStrategy.SLIDING_TOKEN
        assert comparison.best_score == 0.95
        assert comparison.comparison_metadata == {"test": "data"}


class TestChunkingPreflightRequest:
    """Test ChunkingPreflightRequest schema."""

    def test_valid_request(self) -> None:
        """Test creating a valid preflight request."""
        doc_id = uuid4()
        request = ChunkingPreflightRequest(
            document_id=doc_id,
            strategies=[ChunkingStrategy.FIXED_TOKEN, ChunkingStrategy.SLIDING_TOKEN],
            sample_size=2000,
            include_quality_metrics=True,
            include_recommendations=True,
        )

        assert request.document_id == doc_id
        assert len(request.strategies) == 2
        assert request.sample_size == 2000
        assert request.include_quality_metrics is True
        assert request.include_recommendations is True

    def test_default_values(self) -> None:
        """Test default values."""
        doc_id = uuid4()
        request = ChunkingPreflightRequest(
            document_id=doc_id,
            strategies=[ChunkingStrategy.FIXED_TOKEN],
        )

        assert request.sample_size == 1000
        assert request.include_quality_metrics is True
        assert request.include_recommendations is True


class TestChunkingPreflightResponse:
    """Test ChunkingPreflightResponse schema."""

    def test_valid_response(self) -> None:
        """Test creating a valid preflight response."""
        doc_id = uuid4()
        analysis = ChunkingAnalysis(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            document_id=doc_id,
            chunk_count=5,
            avg_chunk_size=400.0,
            size_variance=20.0,
            overlap_ratio=0.2,
            quality_score=0.8,
        )

        response = ChunkingPreflightResponse(
            document_id=doc_id,
            recommended_strategy=ChunkingStrategy.FIXED_TOKEN,
            strategy_scores={
                ChunkingStrategy.FIXED_TOKEN: 0.9,
                ChunkingStrategy.SLIDING_TOKEN: 0.8,
            },
            analysis_results=[analysis],
            processing_time_ms=500,
            recommendations=["Use fixed token strategy"],
        )

        assert response.document_id == doc_id
        assert response.recommended_strategy == ChunkingStrategy.FIXED_TOKEN
        assert len(response.strategy_scores) == 2
        assert len(response.analysis_results) == 1
        assert response.processing_time_ms == 500
        assert response.recommendations == ["Use fixed token strategy"]

    def test_default_recommendations(self) -> None:
        """Test default recommendations."""
        doc_id = uuid4()
        response = ChunkingPreflightResponse(
            document_id=doc_id,
            recommended_strategy=ChunkingStrategy.FIXED_TOKEN,
            strategy_scores={ChunkingStrategy.FIXED_TOKEN: 0.9},
            analysis_results=[],
            processing_time_ms=300,
        )

        assert response.recommendations == []


class TestChunkingFeatureFlags:
    """Test ChunkingFeatureFlags schema."""

    def test_valid_flags(self) -> None:
        """Test creating valid feature flags."""
        flags = ChunkingFeatureFlags(
            enable_expert_chunking=True,
            enable_semantic_adaptive=True,
            enable_page_block=True,
            enable_preflight_analysis=True,
            enable_quality_metrics=True,
            max_concurrent_chunking=5,
        )

        assert flags.enable_expert_chunking is True
        assert flags.enable_semantic_adaptive is True
        assert flags.enable_page_block is True
        assert flags.enable_preflight_analysis is True
        assert flags.enable_quality_metrics is True
        assert flags.max_concurrent_chunking == 5

    def test_default_values(self) -> None:
        """Test default values."""
        flags = ChunkingFeatureFlags()

        assert flags.enable_expert_chunking is False
        assert flags.enable_semantic_adaptive is False
        assert flags.enable_page_block is False
        assert flags.enable_preflight_analysis is True
        assert flags.enable_quality_metrics is True
        assert flags.max_concurrent_chunking == 3

    def test_max_concurrent_validation(self) -> None:
        """Test max concurrent validation."""
        with pytest.raises(ValueError):
            ChunkingFeatureFlags(max_concurrent_chunking=0)  # < 1

        with pytest.raises(ValueError):
            ChunkingFeatureFlags(max_concurrent_chunking=15)  # > 10
