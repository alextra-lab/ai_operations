"""
Integration tests for Circuit Breaker with provider calls.

Tests real circuit breaker behavior with provider interactions
and admin API endpoints.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload

from app.main import app
from app.services.circuit_breaker import CircuitBreaker, CircuitState


class _InMemoryRedis:
    """Minimal async Redis-like store for circuit breaker tests."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    async def hget(self, key: str, field: str):
        return self._store.get(key, {}).get(field)

    async def hset(self, key: str, field: str, value: str):
        self._store.setdefault(key, {})[field] = str(value)
        return 1

    async def hincrby(self, key: str, field: str, amount: int):
        current = int(self._store.get(key, {}).get(field, 0))
        current += amount
        self._store.setdefault(key, {})[field] = str(current)
        return current

    async def expire(self, key: str, _seconds: int):
        return True

    async def delete(self, key: str):
        self._store.pop(key, None)
        return 1


class _RedisWrapper:
    """Wrapper with is_available + client attributes."""

    def __init__(self, client: _InMemoryRedis) -> None:
        self.client = client

    @property
    def is_available(self) -> bool:
        return True


def _build_in_memory_breaker(
    *,
    failure_threshold: int = 3,
    timeout_seconds: int = 60,
    success_threshold: int = 1,
    client: _InMemoryRedis | None = None,
) -> CircuitBreaker:
    client = client or _InMemoryRedis()
    wrapper = _RedisWrapper(client)
    with patch(
        "app.services.circuit_breaker.get_redis_client",
        return_value=wrapper,
    ):
        return CircuitBreaker(
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
            success_threshold=success_threshold,
        )


@pytest.fixture
async def client():
    """Test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def admin_token():
    """Mock admin JWT token."""
    return "mock_admin_token"


@pytest.fixture
def circuit_breaker():
    """Get circuit breaker instance backed by in-memory Redis."""
    return _build_in_memory_breaker()


# === Provider Call Integration ===


@pytest.mark.asyncio
async def test_provider_call_succeeds_when_circuit_closed():
    """Provider call succeeds when circuit CLOSED."""
    from app.providers.base import BaseProvider, ProviderConfig

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="openai",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    provider = BaseProvider(config)

    async def test_func():
        return {"result": "success"}

    # Should execute successfully
    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=_build_in_memory_breaker(),
    ):
        result = await provider.call_with_retry(test_func)

    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_provider_call_opens_circuit_after_failures():
    """Circuit opens after consecutive provider failures."""
    from app.providers.base import BaseProvider, ProviderConfig
    from app.services.circuit_breaker import CircuitOpenError

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="failing-provider",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    provider = BaseProvider(config)

    async def failing_func():
        raise Exception("Provider error")

    breaker = _build_in_memory_breaker()
    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=breaker,
    ):
        # First 3 failures should trigger circuit opening
        for _ in range(3):
            with pytest.raises(Exception):
                await provider.call_with_retry(failing_func)

        # 4th call should fast-fail (circuit OPEN)
        with pytest.raises(CircuitOpenError) as exc_info:
            await provider.call_with_retry(failing_func)

    assert "failing-provider" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_recovers_after_timeout():
    """Circuit transitions to HALF_OPEN after timeout."""
    from app.providers.base import BaseProvider, ProviderConfig

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="recovery-test",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    provider = BaseProvider(config)
    circuit_breaker = _build_in_memory_breaker()

    # Open the circuit manually
    with patch.object(circuit_breaker, "failure_threshold", 1):

        async def failing_func():
            raise Exception("Initial failure")

        with patch(
            "app.services.circuit_breaker.get_circuit_breaker",
            return_value=circuit_breaker,
        ):
            with pytest.raises(Exception):
                await provider.call_with_retry(failing_func)

    # Mock time advancement (simulate timeout)
    real_now = time.time()
    with patch("app.services.circuit_breaker.time.time") as mock_time:
        # Set time 61 seconds in the future
        mock_time.return_value = real_now + 61

        # Circuit should be HALF_OPEN now
        state = await circuit_breaker.get_state("recovery-test")
        assert state == CircuitState.HALF_OPEN


# === Admin API Integration ===


@pytest.mark.asyncio
async def test_get_circuit_breaker_states_endpoint(client, admin_token):
    """GET /admin/circuit-breaker/states returns all provider states."""

    async def _admin_override():
        return TokenPayload(
            sub="admin",
            user_id="admin-id",
            roles=["admin"],
            scopes=[],
            exp=9999999999,
            iat=0,
            iss="test",
            token_type="access",
        )

    fake_breaker = MagicMock()
    fake_breaker.get_all_states = AsyncMock(
        return_value={
            "openai": {
                "state": "CLOSED",
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
                "opened_at": None,
            }
        }
    )

    app.dependency_overrides[admin_required] = _admin_override
    app.dependency_overrides[get_current_user] = _admin_override
    try:
        with patch(
            "app.services.circuit_breaker.get_circuit_breaker",
            return_value=fake_breaker,
        ):
            response = await client.get(
                "/admin/circuit-breaker/states",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should have entries for enabled providers
        if len(data) > 0:
            assert "provider" in data[0]
            assert "state" in data[0]
            assert "failure_count" in data[0]
    finally:
        app.dependency_overrides.pop(admin_required, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_reset_circuit_breaker_endpoint(client, admin_token, circuit_breaker):
    """POST /admin/circuit-breaker/{provider}/reset resets circuit."""

    async def _admin_override():
        return TokenPayload(
            sub="admin",
            user_id="admin-id",
            roles=["admin"],
            scopes=[],
            exp=9999999999,
            iat=0,
            iss="test",
            token_type="access",
        )

    app.dependency_overrides[admin_required] = _admin_override
    app.dependency_overrides[get_current_user] = _admin_override
    try:
        with patch(
            "app.services.circuit_breaker.get_circuit_breaker",
            return_value=circuit_breaker,
        ):
            # Open circuit first
            await circuit_breaker._record_failure("openai")
            await circuit_breaker._record_failure("openai")
            await circuit_breaker._record_failure("openai")

            # Reset via API
            response = await client.post(
                "/admin/circuit-breaker/openai/reset",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 204

            # Verify circuit is CLOSED
            state = await circuit_breaker.get_state("openai")
            assert state == CircuitState.CLOSED
    finally:
        app.dependency_overrides.pop(admin_required, None)
        app.dependency_overrides.pop(get_current_user, None)


# === Error Handling Integration ===


@pytest.mark.asyncio
async def test_circuit_breaker_with_timeout_error():
    """Circuit breaker handles timeout errors correctly."""
    from app.providers.base import BaseProvider, ProviderConfig
    from app.utils.errors import ProviderTimeoutError

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="timeout-provider",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=1,
    )

    provider = BaseProvider(config)

    async def timeout_func():
        import httpx

        raise httpx.TimeoutException("timeout")

    # Should raise timeout and record failure
    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=_build_in_memory_breaker(),
    ):
        with pytest.raises(ProviderTimeoutError):
            await provider.call_with_retry(timeout_func)


@pytest.mark.asyncio
async def test_circuit_breaker_with_http_error():
    """Circuit breaker handles HTTP errors correctly."""
    from app.providers.base import BaseProvider, ProviderConfig
    from app.utils.errors import ProviderHTTPError

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="http-error-provider",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    provider = BaseProvider(config)

    async def http_error_func():
        import httpx

        raise httpx.HTTPStatusError(
            "Error",
            request=None,
            response=AsyncMock(status_code=500, text="Server error"),
        )

    # Should raise HTTP error and record failure
    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=_build_in_memory_breaker(),
    ):
        with pytest.raises(ProviderHTTPError):
            await provider.call_with_retry(http_error_func)


# === State Persistence ===


@pytest.mark.asyncio
async def test_circuit_state_persists_across_instances():
    """Circuit state persists in Redis across CircuitBreaker instances."""
    shared_client = _InMemoryRedis()
    wrapper = _RedisWrapper(shared_client)

    with patch(
        "app.services.circuit_breaker.get_redis_client",
        return_value=wrapper,
    ):
        # Instance 1: Record failures
        breaker1 = CircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise Exception("Failure")

        for _ in range(2):
            try:
                await breaker1.call("persistent-provider", failing_func)
            except Exception:
                pass

        # Instance 2: Should see OPEN state
        breaker2 = CircuitBreaker()
        state = await breaker2.get_state("persistent-provider")

        assert state == CircuitState.OPEN


# === Multiple Providers ===


@pytest.mark.asyncio
async def test_independent_circuit_states_for_providers():
    """Different providers have independent circuit states."""
    from app.providers.base import BaseProvider, ProviderConfig

    openai_config = ProviderConfig(
        id=uuid.uuid4(),
        name="openai",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    mistral_config = ProviderConfig(
        id=uuid.uuid4(),
        name="mistral",
        provider_type="openai_compatible",
        base_url="https://api.mistral.ai/v1",
        api_key="test-key",
    )

    openai_provider = BaseProvider(openai_config)
    mistral_provider = BaseProvider(mistral_config)
    breaker = _build_in_memory_breaker()

    # OpenAI fails 3 times
    async def failing_func():
        raise Exception("OpenAI error")

    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=breaker,
    ):
        for _ in range(3):
            try:
                await openai_provider.call_with_retry(failing_func)
            except Exception:
                pass

        # Mistral should still work (CLOSED)
        async def success_func():
            return "success"

        result = await mistral_provider.call_with_retry(success_func)
        assert result == "success"

        # OpenAI circuit should be OPEN
        openai_state = await breaker.get_state("openai")
        mistral_state = await breaker.get_state("mistral")

        assert openai_state == CircuitState.OPEN
        assert mistral_state == CircuitState.CLOSED


# === Performance ===


@pytest.mark.asyncio
async def test_fast_fail_when_circuit_open():
    """Circuit breaker fast-fails (<10ms) when OPEN."""
    from app.providers.base import BaseProvider, ProviderConfig
    from app.services.circuit_breaker import CircuitOpenError

    config = ProviderConfig(
        id=uuid.uuid4(),
        name="fast-fail-test",
        provider_type="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    provider = BaseProvider(config)
    circuit_breaker = _build_in_memory_breaker()

    # Manually open circuit
    await circuit_breaker._record_failure("fast-fail-test")
    await circuit_breaker._record_failure("fast-fail-test")
    await circuit_breaker._record_failure("fast-fail-test")

    # Measure fast-fail time
    start = time.perf_counter()

    async def slow_func():
        import asyncio

        await asyncio.sleep(1)  # This should NOT execute
        return "success"

    with patch(
        "app.services.circuit_breaker.get_circuit_breaker",
        return_value=circuit_breaker,
    ):
        with pytest.raises(CircuitOpenError):
            await provider.call_with_retry(slow_func)

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should fast-fail in <10ms
    message = f"Fast-fail took {elapsed_ms:.2f}ms (expected <10ms)"
    assert elapsed_ms < 10, message
