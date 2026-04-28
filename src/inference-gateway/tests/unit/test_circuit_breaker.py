"""
Unit tests for CircuitBreaker service.

Tests circuit breaker state transitions, failure tracking,
and Redis/PostgreSQL fallback behavior.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
)


@pytest.fixture
def redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.is_available = True
    client.client = AsyncMock()
    return client


@pytest.fixture
def circuit_breaker(redis_client):
    """CircuitBreaker instance with mocked Redis."""
    with patch("app.services.circuit_breaker.get_redis_client", return_value=redis_client):
        breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=60,
            success_threshold=1,
        )
        yield breaker


# === State Transitions ===


@pytest.mark.asyncio
async def test_initial_state_is_closed(circuit_breaker, redis_client):
    """Circuit breaker starts in CLOSED state."""
    redis_client.client.hget.return_value = None

    state = await circuit_breaker.get_state("openai")

    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_transition_closed_to_open_after_failures(circuit_breaker, redis_client):
    """Circuit opens after reaching failure threshold."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value
    redis_client.client.hincrby.side_effect = [1, 2, 3]  # Failure count increases

    # Record 3 failures
    for _ in range(3):
        await circuit_breaker._record_failure("openai")

    # Verify circuit opened
    redis_client.client.hset.assert_any_call("circuit:openai", "state", CircuitState.OPEN.value)


@pytest.mark.asyncio
async def test_transition_open_to_half_open_after_timeout(circuit_breaker, redis_client):
    """Circuit transitions to HALF_OPEN after timeout."""
    # Set circuit as OPEN 61 seconds ago
    opened_at = time.time() - 61
    redis_client.client.hget.side_effect = [
        CircuitState.OPEN.value,  # Current state
        str(opened_at),  # Opened at timestamp
    ]

    state = await circuit_breaker.get_state("openai")

    assert state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_transition_half_open_to_closed_after_success(circuit_breaker, redis_client):
    """Circuit closes after successful request in HALF_OPEN state."""
    redis_client.client.hget.return_value = CircuitState.HALF_OPEN.value
    redis_client.client.hincrby.return_value = 1  # Success count = 1

    await circuit_breaker._record_success("openai")

    # Verify circuit closed
    redis_client.client.hset.assert_called_with(
        "circuit:openai", "state", CircuitState.CLOSED.value
    )


@pytest.mark.asyncio
async def test_transition_half_open_to_open_after_failure(circuit_breaker, redis_client):
    """Circuit reopens after failure during HALF_OPEN recovery."""
    redis_client.client.hget.return_value = CircuitState.HALF_OPEN.value
    redis_client.client.hincrby.return_value = 1  # Failure count

    await circuit_breaker._record_failure("openai")

    # Verify circuit reopened (check for any call with state=OPEN)
    calls = redis_client.client.hset.call_args_list
    state_calls = [call for call in calls if len(call[0]) == 3 and call[0][1] == "state"]
    assert any(call[0][2] == CircuitState.OPEN.value for call in state_calls)


# === Call Execution ===


@pytest.mark.asyncio
async def test_call_succeeds_when_circuit_closed(circuit_breaker, redis_client):
    """Function executes normally when circuit CLOSED."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value

    async def test_func():
        return "success"

    result = await circuit_breaker.call("openai", test_func)

    assert result == "success"


@pytest.mark.asyncio
async def test_call_fast_fails_when_circuit_open(circuit_breaker, redis_client):
    """Function fast-fails when circuit OPEN."""
    redis_client.client.hget.side_effect = [
        CircuitState.OPEN.value,  # State
        str(time.time()),  # Opened at (recently)
    ]

    async def test_func():
        return "should not execute"

    with pytest.raises(CircuitOpenError) as exc_info:
        await circuit_breaker.call("openai", test_func)

    assert "openai" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_call_records_success(circuit_breaker, redis_client):
    """Successful call increments success count."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value

    async def test_func():
        return "success"

    await circuit_breaker.call("openai", test_func)

    # Verify success recorded
    redis_client.client.hincrby.assert_called_with("circuit:openai", "success_count", 1)
    redis_client.client.hset.assert_called_with("circuit:openai", "failure_count", "0")


@pytest.mark.asyncio
async def test_call_records_failure(circuit_breaker, redis_client):
    """Failed call increments failure count."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value
    redis_client.client.hincrby.return_value = 1  # Failure count

    async def test_func():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await circuit_breaker.call("openai", test_func)

    # Verify failure recorded
    redis_client.client.hincrby.assert_called_with("circuit:openai", "failure_count", 1)
    redis_client.client.hset.assert_any_call("circuit:openai", "success_count", "0")


@pytest.mark.asyncio
async def test_call_works_with_sync_functions(circuit_breaker, redis_client):
    """Circuit breaker handles sync functions."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value

    def sync_func():
        return "sync success"

    result = await circuit_breaker.call("openai", sync_func)

    assert result == "sync success"


# === Reset Functionality ===


@pytest.mark.asyncio
async def test_reset_clears_circuit_state(circuit_breaker, redis_client):
    """Reset clears all circuit state in Redis."""
    await circuit_breaker.reset("openai")

    redis_client.client.delete.assert_called_with("circuit:openai")


# === Get All States ===


@pytest.mark.asyncio
async def test_get_all_states_returns_provider_states(circuit_breaker, redis_client):
    """get_all_states returns state for all enabled providers."""
    # Mock database query
    with patch("app.services.circuit_breaker.get_db") as mock_db:
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("openai",), ("mistral",)]
        mock_db.return_value.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)

        # Mock Redis state data - use a callable to return values based on key
        now = time.time()
        recent_time = now - 10  # Recent enough that circuit stays OPEN

        redis_data = {
            "circuit:openai": {
                "state": CircuitState.CLOSED.value,
                "failure_count": "0",
                "success_count": "5",
                "last_failure_time": None,
                "opened_at": None,
            },
            "circuit:mistral": {
                "state": CircuitState.OPEN.value,
                "failure_count": "3",
                "success_count": "0",
                "last_failure_time": str(now),
                "opened_at": str(recent_time),  # Recent = stays OPEN
            },
        }

        async def mock_hget(key, field):
            """Mock hget that returns values based on key and field."""
            return redis_data.get(key, {}).get(field)

        redis_client.client.hget.side_effect = mock_hget

        states = await circuit_breaker.get_all_states()

        assert "openai" in states
        assert states["openai"]["state"] == "CLOSED"
        assert states["openai"]["failure_count"] == 0
        assert states["openai"]["success_count"] == 5

        assert "mistral" in states
        assert states["mistral"]["state"] == "OPEN"
        assert states["mistral"]["failure_count"] == 3


# === PostgreSQL Fallback ===


@pytest.mark.asyncio
async def test_fallback_to_closed_when_redis_unavailable():
    """Circuit defaults to CLOSED when Redis unavailable."""
    redis_client = MagicMock()
    redis_client.is_available = False

    with patch("app.services.circuit_breaker.get_redis_client", return_value=redis_client):
        breaker = CircuitBreaker()
        state = await breaker.get_state("openai")

        assert state == CircuitState.CLOSED  # Fail-open


# === Configuration ===


def test_get_circuit_breaker_singleton():
    """get_circuit_breaker returns singleton instance."""
    from shared.config.schemas import CircuitBreakerConfig

    from app.services.circuit_breaker import configure_circuit_breaker

    settings = CircuitBreakerConfig(
        failure_threshold=5,
        timeout_seconds=120,
        success_threshold=2,
    )
    with patch("app.services.circuit_breaker._circuit_breaker", None):
        configure_circuit_breaker(settings)
        breaker1 = get_circuit_breaker()
        breaker2 = get_circuit_breaker()

        assert breaker1 is breaker2
        assert breaker1.failure_threshold == 5
        assert breaker1.timeout_seconds == 120
        assert breaker1.success_threshold == 2


# === Retry After Calculation ===


@pytest.mark.asyncio
async def test_retry_after_seconds_calculated_correctly(circuit_breaker, redis_client):
    """retry_after_seconds decreases as timeout approaches."""
    opened_at = time.time() - 30  # Opened 30 seconds ago
    redis_client.client.hget.return_value = str(opened_at)

    retry_after = await circuit_breaker._get_retry_after_seconds("openai")

    assert 25 <= retry_after <= 35  # Should be ~30 seconds remaining


@pytest.mark.asyncio
async def test_retry_after_never_negative(circuit_breaker, redis_client):
    """retry_after_seconds never goes negative."""
    opened_at = time.time() - 100  # Opened long ago
    redis_client.client.hget.return_value = str(opened_at)

    retry_after = await circuit_breaker._get_retry_after_seconds("openai")

    assert retry_after >= 0


# === Edge Cases ===


@pytest.mark.asyncio
async def test_concurrent_calls_with_same_provider(circuit_breaker, redis_client):
    """Multiple concurrent calls handled correctly."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value

    async def slow_func():
        await asyncio.sleep(0.1)
        return "success"

    # Execute 5 calls concurrently
    results = await asyncio.gather(*[circuit_breaker.call("openai", slow_func) for _ in range(5)])

    assert all(r == "success" for r in results)
    # Success count should be incremented 5 times
    assert redis_client.client.hincrby.call_count >= 5


@pytest.mark.asyncio
async def test_handles_redis_errors_gracefully(circuit_breaker, redis_client):
    """Gracefully handles Redis errors."""
    redis_client.client.hget.side_effect = Exception("Redis connection lost")

    # Should default to CLOSED (fail-open)
    state = await circuit_breaker.get_state("openai")
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_multiple_providers_independent(circuit_breaker, redis_client):
    """Each provider has independent circuit state."""
    redis_client.client.hget.return_value = CircuitState.CLOSED.value
    redis_client.client.hincrby.side_effect = [1, 2, 3]  # openai failures

    # openai fails 3 times
    for _ in range(3):
        await circuit_breaker._record_failure("openai")

    # mistral should still be CLOSED (independent)
    mistral_state = await circuit_breaker.get_state("mistral")
    assert mistral_state == CircuitState.CLOSED
