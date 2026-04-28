"""
Integration Tests for P4-DOC-07: Auto Chunking Detection

Tests the core preflight analysis and strategy selection logic.

Test Coverage:
- Preflight analysis runs and returns recommendations
- Strategy scores calculated correctly
- Collection-level preflight settings applied
- Selected strategy is reasonable for document structure
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.corpus_svc.app.db.models import Collection
from src.corpus_svc.app.repositories.collection_repository import (
    CollectionRepository,
)
from src.corpus_svc.app.schemas.chunking_enums import ChunkingStrategy
from src.corpus_svc.app.schemas.collections import CollectionCreate
from src.corpus_svc.app.services.chunking_service import ChunkingService
from src.corpus_svc.app.services.preflight_service import PreflightAnalyzer

# Sample document content for testing
SAMPLE_DOCUMENT_TEXT = """# Test Document for Auto-Chunking

## Introduction
This is a comprehensive test document designed to evaluate the auto-chunking
detection system. It contains various structural elements to test different
chunking strategies.

## Section 1: Structured Content
Content for section 1 with multiple paragraphs. This paragraph contains
enough text to form a meaningful chunk for testing purposes.

This is the second paragraph in section 1. It provides additional context
and helps test paragraph boundary detection.

### Subsection 1.1
Nested heading content to test heading-aware chunking strategies.

## Section 2: Tabular Data

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
| Data 7   | Data 8   | Data 9   |

Tables should be preserved as single chunks when using table-aware strategy.

## Section 3: Lists

1. First item in ordered list
2. Second item with more detailed explanation
3. Third item that extends across multiple lines and contains
   enough text to be meaningful

Unordered list:
- Bullet point one
- Bullet point two with additional context
- Bullet point three

## Conclusion
Final thoughts and summary section. This document should trigger heading-aware
or sentence_paragraph strategy based on structural analysis.
"""


@pytest.fixture
async def test_collection(
    async_session: AsyncSession,
) -> Collection:
    """Create a test collection with preflight configuration."""
    import uuid

    collection_repo = CollectionRepository(async_session)
    unique_name = f"test_auto_chunk_{uuid.uuid4().hex[:8]}"

    collection_data = CollectionCreate.model_validate(
        {
            "name": unique_name,
            "description": "Test collection for auto-chunking",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_provider": "local",
            "embedding_dimensions": 384,
            "preflight_sample_tokens": 5000,  # Smaller sample for faster tests
            "auto_chunk_enabled": True,
            "preflight_strategies": [
                "sentence_paragraph",
                "fixed_token",
                "heading_aware",
            ],
        }
    )

    collection = await collection_repo.create_collection(collection_data, created_by="test_user")
    await async_session.flush()

    return collection


@pytest.mark.asyncio
async def test_preflight_analysis_basic() -> None:
    """
    Test that preflight analysis runs and returns valid recommendations.
    """
    # Arrange: Create chunking service and preflight analyzer
    chunking_service = ChunkingService()
    analyzer = PreflightAnalyzer(chunking_service)

    # Act: Run preflight analysis on sample document
    report = await analyzer.analyze(
        text=SAMPLE_DOCUMENT_TEXT,
        document_name="test.txt",
        document_type="text/plain",
        document_size_bytes=len(SAMPLE_DOCUMENT_TEXT),
        max_sample_tokens=5000,  # Small sample for fast test
        strategies_to_test=[
            ChunkingStrategy.SENTENCE_PARAGRAPH,
            ChunkingStrategy.FIXED_TOKEN,
            ChunkingStrategy.HEADING_AWARE,
        ],
    )

    # Assert: Report generated
    assert report is not None
    assert report.recommendation is not None

    # Assert: Structure signals detected
    assert report.structure_signals is not None
    assert report.structure_signals.heading_density >= 0
    assert report.structure_signals.token_count > 0

    # Assert: Strategies were tested
    assert len(report.strategy_results) >= 3

    # Assert: Each result has scores
    for result in report.strategy_results:
        assert result.chunk_count > 0
        assert result.score >= 0
        assert result.processing_time_ms >= 0

    # Assert: Recommendation is reasonable
    assert report.recommendation.confidence >= 0
    assert report.recommendation.confidence <= 1.0
    assert report.recommendation.reasoning is not None


@pytest.mark.asyncio
async def test_preflight_strategy_scoring() -> None:
    """
    Test that preflight analysis scores different strategies appropriately.
    """
    # Arrange: Create services
    chunking_service = ChunkingService()
    analyzer = PreflightAnalyzer(chunking_service)

    # Act: Analyze document with headings (should favor heading-aware)
    report = await analyzer.analyze(
        text=SAMPLE_DOCUMENT_TEXT,
        document_name="structured_doc.txt",
        document_type="text/plain",
        document_size_bytes=len(SAMPLE_DOCUMENT_TEXT),
        max_sample_tokens=5000,
        strategies_to_test=[
            ChunkingStrategy.HEADING_AWARE,
            ChunkingStrategy.FIXED_TOKEN,
            ChunkingStrategy.SENTENCE_PARAGRAPH,
        ],
    )

    # Assert: Heading density detected (document has multiple headings)
    assert report.structure_signals.heading_density > 0.1

    # Assert: All strategies scored
    assert len(report.strategy_results) == 3
    scores = {r.strategy: r.score for r in report.strategy_results}
    assert all(score >= 0 for score in scores.values())

    # Assert: Recommendation has high confidence for structured document
    assert report.recommendation.confidence > 0.5


@pytest.mark.asyncio
async def test_collection_preflight_settings(
    async_session: AsyncSession,
) -> None:
    """
    Test that collections can be created with custom preflight settings.
    """
    import uuid

    # Arrange: Create collection with custom settings (unique name)
    collection_repo = CollectionRepository(async_session)
    unique_name = f"test_preflight_{uuid.uuid4().hex[:8]}"

    collection_data = CollectionCreate.model_validate(
        {
            "name": unique_name,
            "description": "Collection with custom preflight",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_provider": "local",
            "embedding_dimensions": 384,
            "preflight_sample_tokens": 25000,
            "auto_chunk_enabled": False,  # Disabled
            "preflight_strategies": ["sentence_paragraph"],
        }
    )

    # Act: Create collection
    collection = await collection_repo.create_collection(collection_data, created_by="test_user")
    await async_session.flush()

    # Assert: Settings persisted correctly
    assert collection is not None
    preflight_tokens = getattr(collection, "preflight_sample_tokens", 0)
    assert int(preflight_tokens) == 25000
    assert collection.auto_chunk_enabled is False  # type: ignore[comparison-overlap]

    # Act: Retrieve collection
    retrieved = await collection_repo.get_by_id(collection.id)  # type: ignore[arg-type]
    assert retrieved is not None

    # Assert: Settings retrieved correctly
    retrieved_tokens = getattr(retrieved, "preflight_sample_tokens", 0)
    assert int(retrieved_tokens) == 25000
    assert retrieved.auto_chunk_enabled is False  # type: ignore[comparison-overlap]


@pytest.mark.asyncio
async def test_preflight_recommendation_structure() -> None:
    """
    Test that preflight recommendations include all required fields.
    """
    # Arrange
    chunking_service = ChunkingService()
    analyzer = PreflightAnalyzer(chunking_service)

    # Act
    report = await analyzer.analyze(
        text=SAMPLE_DOCUMENT_TEXT,
        document_name="test.txt",
        document_type="text/plain",
        document_size_bytes=len(SAMPLE_DOCUMENT_TEXT),
        max_sample_tokens=5000,
    )

    # Assert: Recommendation structure
    rec = report.recommendation
    assert hasattr(rec, "strategy")
    assert hasattr(rec, "confidence")
    assert hasattr(rec, "reasoning")
    assert hasattr(rec, "alternative_strategies")

    # Assert: Recommended strategy is valid
    assert rec.strategy in ChunkingStrategy.__members__.values()

    # Assert: Confidence is reasonable
    assert 0 <= rec.confidence <= 1.0

    # Assert: Reasoning provided (list of strings)
    assert isinstance(rec.reasoning, list)
    assert len(rec.reasoning) > 0
    assert all(isinstance(r, str) for r in rec.reasoning)

    # Assert: Alternative strategies provided
    assert isinstance(rec.alternative_strategies, list)
