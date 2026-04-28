"""
Unit tests for Public Configuration Router (ADR-067).

Tests the read-only config endpoints for categories
and intent types with capability profiles.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.config_public import (
    list_categories,
    list_intent_types,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_db_mock(rows: list[dict]) -> AsyncMock:
    """Create an async DB session mock returning *rows*.

    The mock chain mirrors SQLAlchemy async:
        result = await db.execute(...)
        rows   = result.mappings().all()
    ``mappings()`` is a sync method, so use MagicMock.
    """
    db = AsyncMock()
    mappings_obj = MagicMock()
    mappings_obj.all.return_value = rows
    result_obj = MagicMock()
    result_obj.mappings.return_value = mappings_obj
    db.execute.return_value = result_obj
    return db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock async database session (empty result set)."""
    return _make_db_mock([])


@pytest.fixture
def auth_user():
    """Mock authenticated user token payload."""
    from datetime import UTC, datetime

    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="analyst",
        user_id="a0000000-0000-0000-0000-000000000099",
        role="analyst",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


# ============================================================================
# list_categories
# ============================================================================


@pytest.mark.asyncio
async def test_list_categories_returns_all_active(
    auth_user: TokenPayload,
) -> None:
    """Should return all active categories sorted by sort_order."""
    rows = [
        {
            "category_code": "GENERAL",
            "display_name": "General Purpose",
            "description": "General AI",
            "icon": "chat",
            "color": "#607D8B",
            "sort_order": 1,
        },
        {
            "category_code": "SECURITY",
            "display_name": "Security Operations",
            "description": "SOC workflows",
            "icon": "security",
            "color": "#f44336",
            "sort_order": 2,
        },
    ]
    db = _make_db_mock(rows)

    result = await list_categories(_user=auth_user, db=db)

    assert result["total"] == 2
    assert len(result["categories"]) == 2
    assert result["categories"][0].category_code == "GENERAL"
    assert result["categories"][1].category_code == "SECURITY"
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_categories_empty(
    auth_user: TokenPayload,
) -> None:
    """Should return empty list when no categories exist."""
    db = _make_db_mock([])

    result = await list_categories(_user=auth_user, db=db)

    assert result["total"] == 0
    assert result["categories"] == []


# ============================================================================
# list_intent_types
# ============================================================================


@pytest.mark.asyncio
async def test_list_intent_types_returns_profiles(
    auth_user: TokenPayload,
) -> None:
    """Should return intent types with capability profiles."""
    rows = [
        {
            "intent_code": "QUERY",
            "display_name": "General Query",
            "description": "General question answering",
            "category_code": "GENERAL",
            "icon": "question_answer",
            "color": "#2196F3",
            "is_system": True,
            "default_sampling_preset": "balanced",
            "default_output_format": "text",
            "recommended_capabilities": ["general"],
            "sort_order": 1,
        },
        {
            "intent_code": "EXTRACTION",
            "display_name": "Data Extraction",
            "description": "Structured data extraction",
            "category_code": "GENERAL",
            "icon": "find_in_page",
            "color": "#009688",
            "is_system": True,
            "default_sampling_preset": "strict",
            "default_output_format": "json",
            "recommended_capabilities": ["json_mode"],
            "sort_order": 6,
        },
    ]
    db = _make_db_mock(rows)

    result = await list_intent_types(_user=auth_user, db=db)

    assert result["total"] == 2
    types = result["intent_types"]
    assert len(types) == 2
    assert types[0].intent_code == "QUERY"
    assert types[0].default_sampling_preset == "balanced"
    assert types[0].default_output_format == "text"
    assert types[1].intent_code == "EXTRACTION"
    assert types[1].default_sampling_preset == "strict"
    assert types[1].default_output_format == "json"
    assert types[1].recommended_capabilities == ["json_mode"]


@pytest.mark.asyncio
async def test_list_intent_types_empty(
    auth_user: TokenPayload,
) -> None:
    """Should return empty list when no intent types exist."""
    db = _make_db_mock([])

    result = await list_intent_types(_user=auth_user, db=db)

    assert result["total"] == 0
    assert result["intent_types"] == []
