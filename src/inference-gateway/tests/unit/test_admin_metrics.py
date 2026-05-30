"""
Unit tests for admin metrics endpoints.

Tests the Gateway metrics API endpoints without database calls.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.routers.admin import (
    get_aggregate_metrics,
    get_metrics_by_model,
    get_metrics_by_provider,
    get_timeseries_metrics,
)


class MockTokenPayload:
    """Mock token payload for testing."""

    def __init__(
        self,
        sub: str = "admin-user",
        roles: list[Any] | None = None,
    ):
        self.sub = sub
        self.roles = roles or ["admin"]


@pytest.mark.asyncio
async def test_get_aggregate_metrics_success():
    """Test successful aggregate metrics retrieval."""
    # Mock database session and result
    mock_row = (
        100,  # total_requests
        95,  # successful_requests
        5,  # failed_requests
        95.0,  # success_rate
        30000,  # total_input_tokens
        20000,  # total_output_tokens
        0.5,  # total_cost_eur
        150.0,  # avg_latency_ms
        120.0,  # p50_latency_ms
        200.0,  # p95_latency_ms
        250.0,  # p99_latency_ms
        3,  # unique_models
        10,  # unique_users
        40,  # streaming_requests
    )

    with patch("app.routers.admin.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = MockTokenPayload()
        result = await get_aggregate_metrics(hours=24, provider=None, token=token)

        assert result.total_requests == 100
        assert result.successful_requests == 95
        assert result.failed_requests == 5
        assert result.success_rate == 95.0
        assert result.total_input_tokens == 30000
        assert result.total_output_tokens == 20000
        assert result.total_cost_eur == 0.5
        assert result.avg_latency_ms == 150.0
        assert result.p50_latency_ms == 120.0
        assert result.p95_latency_ms == 200.0
        assert result.p99_latency_ms == 250.0
        assert result.unique_models == 3
        assert result.unique_users == 10
        assert result.streaming_requests == 40


@pytest.mark.asyncio
async def test_get_aggregate_metrics_no_data():
    """Test aggregate metrics with no data."""
    with patch("app.routers.admin.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = MockTokenPayload()
        result = await get_aggregate_metrics(hours=24, provider=None, token=token)

        # Should return zeros
        assert result.total_requests == 0
        assert result.successful_requests == 0
        assert result.failed_requests == 0
        assert result.success_rate == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert result.total_cost_eur == 0.0


@pytest.mark.asyncio
async def test_get_metrics_by_provider():
    """Test provider metrics retrieval."""
    mock_rows = [
        ("OpenAI", 50, 98.0, 120.0, 0.25, 25000),
        ("Mistral", 30, 96.0, 100.0, 0.15, 15000),
        ("Local", 20, 100.0, 50.0, 0.0, 10000),
    ]

    with patch("app.routers.admin.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = MockTokenPayload()
        result = await get_metrics_by_provider(hours=24, token=token)

        assert len(result) == 3
        assert result[0].provider_name == "OpenAI"
        assert result[0].request_count == 50
        assert result[0].success_rate == 98.0
        assert result[1].provider_name == "Mistral"
        assert result[2].provider_name == "Local"

        execute_call = mock_db.execute.await_args
        assert execute_call is not None
        assert execute_call.args[1] == {"hours": 24}
        assert ":hours" in str(execute_call.args[0])


@pytest.mark.asyncio
async def test_get_metrics_by_model():
    """Test model metrics retrieval."""
    mock_rows = [
        ("gpt-4", 40, 30000, 0.30, 150.0),
        ("mistral-large", 30, 15000, 0.10, 100.0),
        ("llama2-70b", 20, 10000, 0.05, 80.0),
    ]

    with patch("app.routers.admin.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = MockTokenPayload()
        result = await get_metrics_by_model(hours=24, token=token)

        assert len(result) == 3
        assert result[0].model_name == "gpt-4"
        assert result[0].request_count == 40
        assert result[0].total_tokens == 30000
        assert result[1].model_name == "mistral-large"
        assert result[2].model_name == "llama2-70b"

        execute_call = mock_db.execute.await_args
        assert execute_call is not None
        assert execute_call.args[1] == {"hours": 24}
        assert ":hours" in str(execute_call.args[0])


@pytest.mark.asyncio
async def test_get_timeseries_metrics():
    """Test time-series metrics retrieval."""
    from datetime import datetime

    mock_rows = [
        (datetime(2025, 11, 6, 10, 0), 150.0, 5000, 0.05, 10),
        (datetime(2025, 11, 6, 11, 0), 140.0, 4500, 0.045, 9),
        (datetime(2025, 11, 6, 12, 0), 160.0, 5500, 0.055, 11),
    ]

    with patch("app.routers.admin.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = MockTokenPayload()
        result = await get_timeseries_metrics(
            hours=24, interval_minutes=60, provider=None, token=token
        )

        assert len(result.latency) == 3
        assert len(result.tokens) == 3
        assert len(result.cost) == 3
        assert len(result.requests) == 3

        # Check first data point
        assert result.latency[0].value == 150.0
        assert result.tokens[0].value == 5000
        assert result.cost[0].value == 0.05
        assert result.requests[0].value == 10
