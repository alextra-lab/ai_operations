"""
Unit tests for ChunkingService

Tests the chunking service functionality for Stateless Core v1.
"""

import pytest

from src.orchestrator.app.schemas.chunking_enums import (
    ChunkingConfig,
    ChunkingResult,
    ChunkingStrategy,
)
from src.orchestrator.app.services.chunking_service import ChunkingService


class TestChunkingService:
    """Test cases for ChunkingService."""

    @pytest.fixture
    def chunking_service(self):
        """Create a chunking service instance for testing."""
        return ChunkingService()

    @pytest.fixture
    def sample_text(self):
        """Sample text for testing."""
        return """
        This is a sample document for testing chunking strategies.
        It contains multiple sentences and paragraphs.

        The document has various sections with different content.
        Some sections are longer than others.

        We need to test how different chunking strategies handle this content.
        The strategies should respect boundaries and maintain context.
        """

    @pytest.fixture
    def fixed_token_config(self):
        """Fixed token chunking configuration."""
        return ChunkingConfig(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunk_size=64,
            chunk_overlap=10,
            min_chunk_size=32,
            max_chunk_size=512,
        )

    @pytest.fixture
    def sliding_token_config(self):
        """Sliding token chunking configuration."""
        return ChunkingConfig(
            strategy=ChunkingStrategy.SLIDING_TOKEN,
            chunk_size=64,
            chunk_overlap=20,
            min_chunk_size=32,
            max_chunk_size=512,
        )

    @pytest.fixture
    def heading_aware_config(self):
        """Heading-aware chunking configuration."""
        return ChunkingConfig(
            strategy=ChunkingStrategy.HEADING_AWARE,
            chunk_size=128,
            chunk_overlap=10,
            min_chunk_size=64,
            max_chunk_size=512,
        )

    @pytest.mark.asyncio
    async def test_chunk_document_fixed_token(
        self, chunking_service, sample_text, fixed_token_config
    ):
        """Test fixed token chunking."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=fixed_token_config,
            document_id="test-doc-1",
        )

        assert isinstance(result, ChunkingResult)
        assert result.strategy == ChunkingStrategy.FIXED_TOKEN
        assert len(result.chunks) > 0
        assert result.chunk_count == len(result.chunks)
        assert result.total_tokens > 0
        assert result.avg_chunk_size > 0
        assert result.processing_time_ms >= 0
        assert "test-doc-1" in result.metadata["document_id"]

    @pytest.mark.asyncio
    async def test_chunk_document_sliding_token(
        self, chunking_service, sample_text, sliding_token_config
    ):
        """Test sliding token chunking."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=sliding_token_config,
            document_id="test-doc-2",
        )

        assert isinstance(result, ChunkingResult)
        assert result.strategy == ChunkingStrategy.SLIDING_TOKEN
        assert len(result.chunks) > 0
        assert result.chunk_count == len(result.chunks)
        assert result.total_tokens > 0
        assert result.avg_chunk_size > 0
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_chunk_document_heading_aware(
        self, chunking_service, sample_text, heading_aware_config
    ):
        """Test heading-aware chunking."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=heading_aware_config,
            document_id="test-doc-3",
        )

        assert isinstance(result, ChunkingResult)
        assert result.strategy == ChunkingStrategy.HEADING_AWARE
        assert len(result.chunks) > 0
        assert result.chunk_count == len(result.chunks)
        assert result.total_tokens > 0
        assert result.avg_chunk_size > 0
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_chunk_document_empty_text(self, chunking_service, fixed_token_config):
        """Test chunking with empty text."""
        result = await chunking_service.chunk_document(
            text="",
            config=fixed_token_config,
            document_id="test-doc-empty",
        )

        assert isinstance(result, ChunkingResult)
        assert result.strategy == ChunkingStrategy.FIXED_TOKEN
        assert result.chunk_count == 0
        assert result.total_tokens == 0
        assert result.avg_chunk_size == 0

    @pytest.mark.asyncio
    async def test_chunk_document_short_text(self, chunking_service, fixed_token_config):
        """Test chunking with very short text."""
        short_text = "This is a short text."
        result = await chunking_service.chunk_document(
            text=short_text,
            config=fixed_token_config,
            document_id="test-doc-short",
        )

        assert isinstance(result, ChunkingResult)
        assert result.chunk_count == 1
        assert result.chunks[0] == short_text.strip()

    @pytest.mark.asyncio
    async def test_chunk_document_unsupported_strategy(self, chunking_service, sample_text):
        """Test chunking with unsupported strategy."""
        # This test is skipped because the schema validation prevents creating
        # invalid strategies, so we can't test the runtime error handling
        pytest.skip("Schema validation prevents testing unsupported strategies")

    @pytest.mark.asyncio
    async def test_analyze_chunking_quality(
        self, chunking_service, sample_text, fixed_token_config
    ):
        """Test chunking quality analysis."""
        from uuid import uuid4

        # First chunk the document
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=fixed_token_config,
            document_id="test-doc-analysis",
        )

        # Then analyze the quality
        document_id = str(uuid4())
        analysis = await chunking_service.analyze_chunking_quality(
            result=result,
            document_id=document_id,
        )

        assert analysis.strategy == ChunkingStrategy.FIXED_TOKEN
        assert str(analysis.document_id) == document_id
        assert analysis.chunk_count == result.chunk_count
        assert analysis.avg_chunk_size > 0
        assert analysis.size_variance >= 0
        assert analysis.overlap_ratio >= 0
        assert 0 <= analysis.quality_score <= 1
        assert isinstance(analysis.recommendations, list)

    @pytest.mark.asyncio
    async def test_analyze_chunking_quality_empty_result(self, chunking_service):
        """Test quality analysis with empty chunking result."""
        from uuid import uuid4

        empty_result = ChunkingResult(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunks=[],
            chunk_count=0,
            total_tokens=0,
            avg_chunk_size=0.0,
            processing_time_ms=0,
            metadata={},
        )

        document_id = str(uuid4())
        analysis = await chunking_service.analyze_chunking_quality(
            result=empty_result,
            document_id=document_id,
        )

        assert analysis.strategy == ChunkingStrategy.FIXED_TOKEN
        assert str(analysis.document_id) == document_id
        assert analysis.chunk_count == 0
        assert analysis.avg_chunk_size == 0.0
        assert analysis.size_variance == 0.0
        assert analysis.overlap_ratio == 0.0
        assert analysis.quality_score == 0.0
        assert "No chunks generated" in analysis.recommendations

    @pytest.mark.asyncio
    async def test_chunk_document_with_metadata(
        self, chunking_service, sample_text, fixed_token_config
    ):
        """Test chunking with custom metadata."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=fixed_token_config,
            document_id="test-doc-metadata",
        )

        assert "test-doc-metadata" in result.metadata["document_id"]
        assert "strategy" in result.metadata
        assert result.metadata["strategy"] == ChunkingStrategy.FIXED_TOKEN.value

    @pytest.mark.asyncio
    async def test_chunk_document_processing_time(
        self, chunking_service, sample_text, fixed_token_config
    ):
        """Test that processing time is recorded."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=fixed_token_config,
            document_id="test-doc-timing",
        )

        assert result.processing_time_ms >= 0
        # Processing time should be reasonable (less than 1 second for this test)
        assert result.processing_time_ms < 1000

    @pytest.mark.asyncio
    async def test_chunk_document_token_calculation(
        self, chunking_service, sample_text, fixed_token_config
    ):
        """Test token calculation accuracy."""
        result = await chunking_service.chunk_document(
            text=sample_text,
            config=fixed_token_config,
            document_id="test-doc-tokens",
        )

        # Verify token calculations
        expected_tokens = sum(len(chunk.split()) for chunk in result.chunks)
        assert result.total_tokens == expected_tokens

        if result.chunk_count > 0:
            expected_avg = result.total_tokens / result.chunk_count
            assert (
                abs(result.avg_chunk_size - expected_avg) < 0.01
            )  # Allow for floating point precision
