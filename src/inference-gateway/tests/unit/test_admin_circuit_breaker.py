"""
Unit tests for admin circuit breaker endpoints.

Tests the circuit breaker management API endpoints.

P5-A15: Added comprehensive unit tests for async admin endpoints.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.routers.admin import get_circuit_breaker_states, reset_circuit_breaker


@pytest.fixture
def mock_token():
    """Mock JWT token payload."""
    token = MagicMock()
    token.sub = "admin-user"
    token.user_id = "admin-uuid"
    token.role = "admin"
    return token


@pytest.mark.asyncio
class TestGetCircuitBreakerStates:
    """Test get_circuit_breaker_states endpoint."""

    async def test_get_states_success(self, mock_token):
        """Test successful retrieval of circuit breaker states."""
        now = time.time()
        mock_states = {
            "openai": {
                "state": "CLOSED",
                "failure_count": 0,
                "success_count": 15,
                "last_failure_time": None,
                "opened_at": None,
            },
            "mistral": {
                "state": "OPEN",
                "failure_count": 5,
                "success_count": 0,
                "last_failure_time": now - 30,
                "opened_at": now - 30,
            },
            "anthropic": {
                "state": "HALF_OPEN",
                "failure_count": 3,
                "success_count": 1,
                "last_failure_time": now - 70,
                "opened_at": now - 70,
            },
        }

        # Patch at the service module level (imported inside functions)
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.get_all_states.return_value = mock_states
            mock_get_cb.return_value = mock_cb

            result = await get_circuit_breaker_states(token=mock_token)

            assert len(result) == 3

            # Check openai
            openai_state = next(r for r in result if r.provider == "openai")
            assert openai_state.state == "CLOSED"
            assert openai_state.failure_count == 0
            assert openai_state.success_count == 15
            assert openai_state.last_failure_time is None
            assert openai_state.opened_at is None

            # Check mistral
            mistral_state = next(r for r in result if r.provider == "mistral")
            assert mistral_state.state == "OPEN"
            assert mistral_state.failure_count == 5
            assert mistral_state.success_count == 0
            assert mistral_state.last_failure_time is not None

            # Check anthropic
            anthropic_state = next(r for r in result if r.provider == "anthropic")
            assert anthropic_state.state == "HALF_OPEN"

    async def test_get_states_empty(self, mock_token):
        """Test retrieval with no configured providers."""
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.get_all_states.return_value = {}
            mock_get_cb.return_value = mock_cb

            result = await get_circuit_breaker_states(token=mock_token)

            assert len(result) == 0

    async def test_get_states_error_handling(self, mock_token):
        """Test error handling for circuit breaker state retrieval."""
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.get_all_states.side_effect = Exception("Redis connection error")
            mock_get_cb.return_value = mock_cb

            with pytest.raises(Exception):  # HTTPException 500
                await get_circuit_breaker_states(token=mock_token)


@pytest.mark.asyncio
class TestResetCircuitBreaker:
    """Test reset_circuit_breaker endpoint."""

    async def test_reset_success(self, mock_token):
        """Test successful circuit breaker reset."""
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.reset = AsyncMock()
            mock_get_cb.return_value = mock_cb

            # Should not raise any exception
            await reset_circuit_breaker(provider="openai", token=mock_token)

            # Verify reset was called
            mock_cb.reset.assert_awaited_once_with("openai")

    async def test_reset_different_providers(self, mock_token):
        """Test resetting different provider circuits."""
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.reset = AsyncMock()
            mock_get_cb.return_value = mock_cb

            # Reset multiple providers
            for provider in ["openai", "mistral", "anthropic"]:
                await reset_circuit_breaker(provider=provider, token=mock_token)

            assert mock_cb.reset.await_count == 3

    async def test_reset_error_handling(self, mock_token):
        """Test error handling for circuit breaker reset."""
        with patch("app.services.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = AsyncMock()
            mock_cb.reset.side_effect = Exception("Redis error")
            mock_get_cb.return_value = mock_cb

            with pytest.raises(Exception):  # HTTPException 500
                await reset_circuit_breaker(provider="openai", token=mock_token)
