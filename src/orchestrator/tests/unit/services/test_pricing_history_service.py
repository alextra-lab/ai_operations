"""
Unit tests for PricingHistoryService.

Tests per-model pricing history operations with async patterns.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.db.models import ModelPricingHistory
from app.services.pricing_history_service import PricingHistoryService


@pytest.fixture
def db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def service(db):
    """Create a PricingHistoryService instance."""
    return PricingHistoryService(db)


@pytest.fixture
def mock_model():
    """Create a mock Model."""
    model = MagicMock()
    model.id = uuid4()
    model.model_id = "gpt-4o-mini"
    model.input_price_per_million = 1.5
    model.output_price_per_million = 2.5
    return model


@pytest.fixture
def mock_pricing_history():
    """Create a mock ModelPricingHistory."""
    history = MagicMock()
    history.id = uuid4()
    history.model_id = uuid4()
    history.input_price_per_million = 1.0
    history.output_price_per_million = 2.0
    history.effective_from = datetime.now(UTC) - timedelta(days=1)
    history.effective_to = None
    return history


@pytest.mark.asyncio
async def test_get_active_price_by_model_id_found(service, db, mock_model, mock_pricing_history):
    """Test getting active price by model ID when found."""
    # Mock model lookup
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = mock_model

    # Mock pricing history lookup
    history_result = MagicMock()
    history_result.scalar_one_or_none.return_value = mock_pricing_history

    db.execute = AsyncMock(side_effect=[model_result, history_result])

    result = await service.get_active_price_by_model_id("gpt-4o-mini")

    assert result is not None
    assert result == (1.0, 2.0)


@pytest.mark.asyncio
async def test_get_active_price_by_model_id_not_found(service, db):
    """Test getting active price when model not found."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=model_result)

    result = await service.get_active_price_by_model_id("unknown-model")

    assert result is None


@pytest.mark.asyncio
async def test_get_active_price_by_model_id_fallback_to_model_fields(service, db, mock_model):
    """Test fallback to model registry fields when no pricing history."""
    # Mock model lookup
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = mock_model

    # Mock pricing history lookup (returns None)
    history_result = MagicMock()
    history_result.scalar_one_or_none.return_value = None

    # Mock model lookup for fallback
    model_fallback_result = MagicMock()
    model_fallback_result.scalar_one_or_none.return_value = mock_model

    db.execute = AsyncMock(side_effect=[model_result, history_result, model_fallback_result])

    result = await service.get_active_price_by_model_id("gpt-4o-mini")

    assert result is not None
    assert result == (1.5, 2.5)


@pytest.mark.asyncio
async def test_get_active_price_by_model_uuid_found(service, db, mock_pricing_history):
    """Test getting active price by model UUID when found."""
    model_uuid = uuid4()
    history_result = MagicMock()
    history_result.scalar_one_or_none.return_value = mock_pricing_history
    db.execute = AsyncMock(return_value=history_result)

    result = await service.get_active_price_by_model_uuid(model_uuid)

    assert result is not None
    assert result == (1.0, 2.0)


@pytest.mark.asyncio
async def test_set_price_change_success(service, db, mock_model):
    """Test setting a price change successfully."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = mock_model

    # Mock active pricing history lookup (returns None - no active record)
    history_result = MagicMock()
    history_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[model_result, history_result])
    db.flush = AsyncMock()

    # Don't mock ModelPricingHistory - use the real class
    result = await service.set_price_change(
        model_id_str="gpt-4o-mini",
        input_price_per_million=2.0,
        output_price_per_million=3.0,
        effective_from=None,
        changed_by_user_id=str(uuid4()),
        change_reason="Test price update",
    )

    assert isinstance(result, ModelPricingHistory)
    assert result.input_price_per_million == 2.0
    assert result.output_price_per_million == 3.0
    db.add.assert_called()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_set_price_change_closes_active_record(service, db, mock_model, mock_pricing_history):
    """Test that setting price change closes existing active record."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = mock_model

    # Mock active pricing history lookup (returns existing active record)
    history_result = MagicMock()
    history_result.scalar_one_or_none.return_value = mock_pricing_history

    db.execute = AsyncMock(side_effect=[model_result, history_result])
    db.flush = AsyncMock()

    effective_from = datetime.now(UTC)
    result = await service.set_price_change(
        model_id_str="gpt-4o-mini",
        input_price_per_million=2.0,
        output_price_per_million=3.0,
        effective_from=effective_from,
        changed_by_user_id=str(uuid4()),
        change_reason="Test price update",
    )

    # Verify active record was closed
    assert mock_pricing_history.effective_to == effective_from
    assert isinstance(result, ModelPricingHistory)
    db.add.assert_called()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_set_price_change_model_not_found(service, db):
    """Test setting price change when model not found."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=model_result)

    with pytest.raises(ValueError, match="Unknown model_id"):
        await service.set_price_change(
            model_id_str="unknown-model",
            input_price_per_million=2.0,
            output_price_per_million=3.0,
            effective_from=None,
            changed_by_user_id=str(uuid4()),
            change_reason="Test",
        )


@pytest.mark.asyncio
async def test_set_price_change_negative_price(service, db):
    """Test that negative prices raise ValueError."""
    with pytest.raises(ValueError, match="Prices must be non-negative"):
        await service.set_price_change(
            model_id_str="gpt-4o-mini",
            input_price_per_million=-1.0,
            output_price_per_million=2.0,
            effective_from=None,
            changed_by_user_id=str(uuid4()),
            change_reason="Test",
        )


@pytest.mark.asyncio
async def test_get_price_history_found(service, db, mock_model):
    """Test getting price history when found."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = mock_model

    history_records = [MagicMock(), MagicMock()]
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = history_records

    db.execute = AsyncMock(side_effect=[model_result, history_result])

    result = await service.get_price_history("gpt-4o-mini")

    assert len(list(result)) == 2


@pytest.mark.asyncio
async def test_get_price_history_model_not_found(service, db):
    """Test getting price history when model not found."""
    model_result = MagicMock()
    model_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=model_result)

    result = await service.get_price_history("unknown-model")

    assert list(result) == []
