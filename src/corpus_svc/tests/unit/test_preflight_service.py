"""
Unit tests for PreflightAnalyzer service.

Tests document structure analysis and chunking strategy recommendation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.corpus_svc.app.schemas.chunking_enums import (
    ChunkingResult,
    ChunkingStrategy,
)
from src.corpus_svc.app.services.preflight_service import PreflightAnalyzer


@pytest.fixture
def mock_chunking_service():
    """Create mock chunking service."""
    service = MagicMock()
    service.chunk_document = AsyncMock()
    return service


@pytest.fixture
def preflight_analyzer(mock_chunking_service):
    """Create PreflightAnalyzer instance with mocked dependencies."""
    return PreflightAnalyzer(mock_chunking_service)


class TestStructureAnalysis:
    """Tests for _analyze_structure method."""

    def test_analyze_markdown_document(self, preflight_analyzer):
        """Test structure analysis for Markdown document."""
        text = """# Heading 1

This is a paragraph with some content.

## Heading 2

- List item 1
- List item 2
- List item 3

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""

        signals = preflight_analyzer._analyze_structure(text)

        assert signals.heading_density > 0.0
        assert signals.table_ratio > 0.0
        assert signals.list_ratio > 0.0
        assert signals.sentence_count > 0
        assert signals.token_count > 0
        assert signals.has_code_blocks is False
        assert signals.has_equations is False

    def test_analyze_code_document(self, preflight_analyzer):
        """Test structure analysis detects code blocks."""
        text = """# Documentation

Here's a code example:

```python
def hello():
    print("Hello, World!")
```
"""

        signals = preflight_analyzer._analyze_structure(text)

        assert signals.has_code_blocks is True

    def test_analyze_equation_document(self, preflight_analyzer):
        """Test structure analysis detects equations."""
        text = """# Math Document

Einstein's equation: $E = mc^2$

More complex: $$\\int_0^\\infty e^{-x} dx = 1$$
"""

        signals = preflight_analyzer._analyze_structure(text)

        assert signals.has_equations is True

    def test_analyze_plain_text(self, preflight_analyzer):
        """Test structure analysis for plain text."""
        text = "This is plain text without any structure. " * 50

        signals = preflight_analyzer._analyze_structure(text)

        assert signals.heading_density == 0.0
        assert signals.table_ratio == 0.0
        assert signals.avg_paragraph_length > 0
        assert signals.token_count > 0


class TestSampleExtraction:
    """Tests for _extract_sample method."""

    def test_extract_sample_small_document(self, preflight_analyzer):
        """Test sample extraction for small document."""
        text = "Short document with only a few words."

        sample = preflight_analyzer._extract_sample(text, max_tokens=100)

        assert sample == text

    def test_extract_sample_large_document(self, preflight_analyzer):
        """Test sample extraction limits to max_tokens."""
        words = ["word"] * 1000
        text = " ".join(words)

        sample = preflight_analyzer._extract_sample(text, max_tokens=100)

        sample_words = sample.split()
        assert len(sample_words) == 100


class TestDefaultStrategies:
    """Tests for _get_default_strategies method."""

    def test_default_strategies_count(self, preflight_analyzer):
        """Test default strategies returns 5 core strategies."""
        strategies = preflight_analyzer._get_default_strategies()

        assert len(strategies) == 5
        assert ChunkingStrategy.FIXED_TOKEN in strategies
        assert ChunkingStrategy.SLIDING_TOKEN in strategies
        assert ChunkingStrategy.HEADING_AWARE in strategies
        assert ChunkingStrategy.SENTENCE_PARAGRAPH in strategies
        assert ChunkingStrategy.TABLE_AWARE in strategies


class TestStrategyScoring:
    """Tests for _calculate_strategy_score method."""

    def test_heading_aware_score_high_for_structured(self, preflight_analyzer):
        """Test heading-aware strategy scores high for structured docs."""
        from src.corpus_svc.app.schemas.preflight import StructureSignals

        signals = StructureSignals(
            heading_density=0.8,  # High heading density
            table_ratio=0.1,
            list_ratio=0.2,
            avg_paragraph_length=50.0,
            sentence_count=100,
            token_count=2000,
            has_code_blocks=False,
            ocr_confidence=None,
            has_equations=False,
        )

        score = preflight_analyzer._calculate_strategy_score(
            strategy=ChunkingStrategy.HEADING_AWARE,
            structure_signals=signals,
            chunk_count=10,
            avg_chunk_size=200.0,
            std_chunk_size=20.0,
            hit_at_k=None,
            mrr=None,
        )

        # Should score high due to heading_density
        assert score > 0.5

    def test_table_aware_score_high_for_tables(self, preflight_analyzer):
        """Test table-aware strategy scores high for tabular docs."""
        from src.corpus_svc.app.schemas.preflight import StructureSignals

        signals = StructureSignals(
            heading_density=0.1,
            table_ratio=0.8,  # High table ratio
            list_ratio=0.1,
            avg_paragraph_length=30.0,
            sentence_count=50,
            token_count=1000,
            has_code_blocks=False,
            has_equations=False,
            ocr_confidence=None,
        )

        score = preflight_analyzer._calculate_strategy_score(
            strategy=ChunkingStrategy.TABLE_AWARE,
            structure_signals=signals,
            chunk_count=5,
            avg_chunk_size=200.0,
            std_chunk_size=10.0,
            hit_at_k=None,
            mrr=None,
        )

        # Should score high due to table_ratio
        assert score > 0.5

    def test_score_with_retrieval_metrics(self, preflight_analyzer):
        """Test scoring includes retrieval metrics when available."""
        from src.corpus_svc.app.schemas.preflight import StructureSignals

        signals = StructureSignals(
            heading_density=0.3,
            table_ratio=0.2,
            list_ratio=0.1,
            avg_paragraph_length=80.0,
            sentence_count=100,
            token_count=2000,
            has_code_blocks=False,
            has_equations=False,
            ocr_confidence=None,
        )

        score_without_metrics = preflight_analyzer._calculate_strategy_score(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            structure_signals=signals,
            chunk_count=10,
            avg_chunk_size=200.0,
            std_chunk_size=20.0,
            hit_at_k=None,
            mrr=None,
        )

        score_with_metrics = preflight_analyzer._calculate_strategy_score(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            structure_signals=signals,
            chunk_count=10,
            avg_chunk_size=200.0,
            std_chunk_size=20.0,
            hit_at_k=0.9,
            mrr=0.8,
        )

        # Score with good retrieval metrics should be higher
        assert score_with_metrics > score_without_metrics


class TestStrategyRecommendation:
    """Tests for _select_best_strategy method."""

    def test_select_best_strategy_by_score(self, preflight_analyzer):
        """Test best strategy selection based on score."""
        from src.corpus_svc.app.schemas.preflight import (
            StrategyBenchmarkResult,
            StructureSignals,
        )

        signals = StructureSignals(
            heading_density=0.8,
            table_ratio=0.1,
            list_ratio=0.2,
            avg_paragraph_length=50.0,
            sentence_count=100,
            token_count=2000,
            has_code_blocks=False,
            has_equations=False,
            ocr_confidence=None,
        )

        results = [
            StrategyBenchmarkResult(
                strategy=ChunkingStrategy.HEADING_AWARE,
                chunk_count=10,
                avg_chunk_size=200.0,
                std_chunk_size=20.0,
                processing_time_ms=100,
                score=0.85,  # Highest score
                hit_at_k=0.9,
                mrr=0.85,
                ndcg=0.88,
                zero_result_rate=0.05,
                rank=1,
            ),
            StrategyBenchmarkResult(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_count=12,
                avg_chunk_size=180.0,
                std_chunk_size=15.0,
                processing_time_ms=80,
                score=0.65,
                hit_at_k=0.75,
                mrr=0.70,
                ndcg=0.72,
                zero_result_rate=0.10,
                rank=2,
            ),
        ]

        recommendation = preflight_analyzer._select_best_strategy(results, signals)

        assert recommendation.strategy == ChunkingStrategy.HEADING_AWARE
        assert recommendation.confidence > 0.0
        assert len(recommendation.reasoning) > 0
        assert ChunkingStrategy.FIXED_TOKEN in recommendation.alternative_strategies

    def test_recommendation_includes_structure_reasoning(self, preflight_analyzer):
        """Test recommendation includes structure-based reasoning."""
        from src.corpus_svc.app.schemas.preflight import (
            StrategyBenchmarkResult,
            StructureSignals,
        )

        signals = StructureSignals(
            heading_density=0.9,  # Very high
            table_ratio=0.5,  # High
            list_ratio=0.1,
            avg_paragraph_length=150.0,  # Long
            sentence_count=100,
            token_count=5000,
            has_code_blocks=True,
            has_equations=True,
            ocr_confidence=None,
        )

        results = [
            StrategyBenchmarkResult(
                strategy=ChunkingStrategy.HEADING_AWARE,
                chunk_count=10,
                avg_chunk_size=200.0,
                std_chunk_size=20.0,
                processing_time_ms=100,
                score=0.9,
                hit_at_k=0.92,
                mrr=0.88,
                ndcg=0.90,
                zero_result_rate=0.03,
                rank=1,
            ),
        ]

        recommendation = preflight_analyzer._select_best_strategy(results, signals)

        # Should mention high heading density
        reasoning_text = " ".join(recommendation.reasoning)
        assert "heading" in reasoning_text.lower()

    def test_high_confidence_threshold(self, preflight_analyzer):
        """Test high confidence for clear winner."""
        from src.corpus_svc.app.schemas.preflight import (
            StrategyBenchmarkResult,
            StructureSignals,
        )

        signals = StructureSignals(
            heading_density=0.5,
            table_ratio=0.2,
            list_ratio=0.1,
            avg_paragraph_length=80.0,
            sentence_count=100,
            token_count=2000,
            has_code_blocks=False,
            has_equations=False,
            ocr_confidence=None,
        )

        results = [
            StrategyBenchmarkResult(
                strategy=ChunkingStrategy.HEADING_AWARE,
                chunk_count=10,
                avg_chunk_size=200.0,
                std_chunk_size=20.0,
                processing_time_ms=100,
                score=0.95,  # Very high score
                hit_at_k=0.96,
                mrr=0.93,
                ndcg=0.95,
                zero_result_rate=0.02,
                rank=1,
            ),
            StrategyBenchmarkResult(
                strategy=ChunkingStrategy.FIXED_TOKEN,
                chunk_count=12,
                avg_chunk_size=180.0,
                std_chunk_size=15.0,
                processing_time_ms=80,
                score=0.50,  # Much lower
                hit_at_k=0.62,
                mrr=0.58,
                ndcg=0.60,
                zero_result_rate=0.18,
                rank=2,
            ),
        ]

        recommendation = preflight_analyzer._select_best_strategy(results, signals)

        # High score gap should produce high confidence
        assert recommendation.confidence > 0.8


@pytest.mark.asyncio
class TestPreflightAnalysis:
    """Integration tests for analyze method."""

    async def test_analyze_completes(self, preflight_analyzer, mock_chunking_service):
        """Test analyze method completes without error."""
        # Mock chunking service to return results
        mock_chunking_service.chunk_document.return_value = ChunkingResult(
            strategy=ChunkingStrategy.FIXED_TOKEN,
            chunks=["chunk1", "chunk2", "chunk3"],
            chunk_count=3,
            total_tokens=600,
            avg_chunk_size=200.0,
            processing_time_ms=50,
            metadata={},
        )

        text = "Sample document text. " * 100

        report = await preflight_analyzer.analyze(
            text=text,
            document_name="test.txt",
            document_type="text/plain",
            document_size_bytes=len(text),
            test_suite_id=None,
            strategies_to_test=None,
            max_sample_tokens=500,
        )

        assert report.document_name == "test.txt"
        assert report.document_type == "text/plain"
        assert report.structure_signals is not None
        assert len(report.strategy_results) == 5  # 5 default strategies
        assert report.recommendation is not None
        assert isinstance(report.recommendation.strategy, ChunkingStrategy)
        assert 0.0 <= report.recommendation.confidence <= 1.0
        assert report.analysis_time_ms >= 0
