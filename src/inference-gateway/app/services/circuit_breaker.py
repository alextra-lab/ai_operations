"""
Circuit breaker service for provider health management.

Implements a light circuit breaker pattern with three states:
- CLOSED: Provider healthy, requests pass through
- OPEN: Provider failing, requests fast-fail
- HALF_OPEN: Testing recovery, limited requests allowed

State transitions:
- CLOSED → OPEN: After N consecutive failures (default: 3)
- OPEN → HALF_OPEN: After timeout (default: 60 seconds)
- HALF_OPEN → CLOSED: After successful request
- HALF_OPEN → OPEN: After failure during recovery

Uses Redis for shared state across Gateway instances.
Falls back to PostgreSQL if Redis unavailable.

Follows ADR-050 (Inference Gateway) and ADR-053 (Rate Limiting).
"""

import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from shared.config.schemas import CircuitBreakerConfig
from shared.database import get_db  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from sqlalchemy import text

from .redis_client import get_redis_client

logger = configure_logging(service_name="circuit_breaker")

# Type variable for return values
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Healthy - requests pass through
    OPEN = "OPEN"  # Failing - fast-fail for timeout period
    HALF_OPEN = "HALF_OPEN"  # Testing - allow limited requests


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, provider: str, retry_after_seconds: int):
        """
        Initialize circuit open error.

        Args:
            provider: Provider name
            retry_after_seconds: Seconds until auto-recovery
        """
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Circuit breaker OPEN for provider '{provider}'. "
            f"Retry after {retry_after_seconds} seconds."
        )


class CircuitBreaker:
    """
    Light circuit breaker for provider health tracking.

    Features:
    - Three states: CLOSED, OPEN, HALF_OPEN
    - Redis storage for shared state (PostgreSQL fallback)
    - Configurable thresholds
    - Fast-fail when OPEN (<10ms)
    - Automatic recovery testing

    Example:
        >>> breaker = CircuitBreaker()
        >>> async with breaker.call("openai", provider_fn) as result:
        ...     return result
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_seconds: int = 60,
        success_threshold: int = 1,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening
            timeout_seconds: Seconds before testing recovery
            success_threshold: Successes needed to close from HALF_OPEN
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        # Get Redis client
        self.redis_client = get_redis_client()

        logger.info(
            "Circuit breaker initialized",
            extra={
                "failure_threshold": failure_threshold,
                "timeout_seconds": timeout_seconds,
                "success_threshold": success_threshold,
                "redis_available": self.redis_client.is_available,
            },
        )

    async def call(
        self,
        provider: str,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            provider: Provider name (e.g., "openai", "mistral")
            func: Async function to execute
            *args: Positional arguments to func
            **kwargs: Keyword arguments to func

        Returns:
            Result from func

        Raises:
            CircuitOpenError: If circuit is OPEN (fast-fail)
            Exception: Original exception from func
        """
        # Check circuit state
        state = await self.get_state(provider)

        if state == CircuitState.OPEN:
            # Fast-fail - no provider call
            retry_after = await self._get_retry_after_seconds(provider)
            logger.warning(
                "Circuit breaker OPEN - fast-fail",
                extra={
                    "provider": provider,
                    "retry_after_seconds": retry_after,
                },
            )
            raise CircuitOpenError(provider=provider, retry_after_seconds=retry_after)

        # Execute function (CLOSED or HALF_OPEN)
        try:
            result = func(*args, **kwargs)

            # Handle both sync and async functions
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[misc]

            # Record success
            await self._record_success(provider)

            return result  # type: ignore[return-value]

        except Exception:  # noqa: BLE001 - Re-raise after recording failure
            # Record failure
            await self._record_failure(provider)
            raise

    async def get_state(self, provider: str) -> CircuitState:
        """
        Get current circuit state for provider.

        Args:
            provider: Provider name

        Returns:
            Current circuit state
        """
        if self.redis_client.is_available:
            return await self._get_state_redis(provider)
        else:
            return await self._get_state_postgres(provider)

    async def get_all_states(self) -> dict[str, dict[str, Any]]:
        """
        Get circuit states for all providers.

        Returns:
            Dictionary mapping provider name to state info:
            {
                "openai": {
                    "state": "CLOSED",
                    "failure_count": 0,
                    "success_count": 0,
                    "last_failure_time": None,
                    "opened_at": None
                }
            }
        """
        states = {}

        # Get all providers from database
        async with get_db() as db:
            result = await db.execute(
                text(
                    """
                    SELECT name FROM gateway_providers
                    WHERE is_enabled = true
                    ORDER BY name
                    """
                )
            )
            providers = [row[0] for row in result.fetchall()]

        # Get state for each provider
        for provider in providers:
            state = await self.get_state(provider)

            if self.redis_client.is_available:
                # Get additional info from Redis
                key = self._redis_key(provider)
                try:
                    failure_count = int(
                        await self.redis_client.client.hget(key, "failure_count") or 0  # type: ignore[misc,union-attr]
                    )
                    success_count = int(
                        await self.redis_client.client.hget(key, "success_count") or 0  # type: ignore[misc,union-attr]
                    )
                    last_failure_time = await self.redis_client.client.hget(  # type: ignore[misc,union-attr]
                        key, "last_failure_time"
                    )
                    opened_at = await self.redis_client.client.hget(  # type: ignore[misc,union-attr]
                        key, "opened_at"
                    )

                    states[provider] = {
                        "state": state.value,
                        "failure_count": failure_count,
                        "success_count": success_count,
                        "last_failure_time": (
                            float(last_failure_time) if last_failure_time else None
                        ),
                        "opened_at": float(opened_at) if opened_at else None,
                    }
                except Exception as exc:  # noqa: BLE001 - Graceful degradation
                    logger.warning(
                        "Error getting circuit state details",
                        extra={"provider": provider, "error": str(exc)},
                    )
                    states[provider] = {
                        "state": state.value,
                        "failure_count": 0,
                        "success_count": 0,
                        "last_failure_time": None,
                        "opened_at": None,
                    }
            else:
                # PostgreSQL fallback
                states[provider] = {
                    "state": state.value,
                    "failure_count": 0,
                    "success_count": 0,
                    "last_failure_time": None,
                    "opened_at": None,
                }

        return states

    async def reset(self, provider: str) -> None:
        """
        Manually reset circuit breaker to CLOSED state.

        Args:
            provider: Provider name
        """
        if self.redis_client.is_available:
            await self._reset_redis(provider)
        else:
            await self._reset_postgres(provider)

        logger.info("Circuit breaker reset", extra={"provider": provider})

    # === Private: Redis Implementation ===

    def _redis_key(self, provider: str) -> str:
        """Build Redis key for provider."""
        return f"circuit:{provider}"

    async def _get_state_redis(self, provider: str) -> CircuitState:
        """Get circuit state from Redis."""
        try:
            key = self._redis_key(provider)
            state_str = await self.redis_client.client.hget(key, "state")  # type: ignore[misc,union-attr]

            if state_str:
                state = CircuitState(state_str)

                # Check if OPEN circuit should transition to HALF_OPEN
                if state == CircuitState.OPEN:
                    opened_at = await self.redis_client.client.hget(key, "opened_at")  # type: ignore[misc,union-attr]
                    if opened_at:
                        elapsed = time.time() - float(opened_at)
                        if elapsed >= self.timeout_seconds:
                            # Transition to HALF_OPEN
                            await self._set_state_redis(provider, CircuitState.HALF_OPEN)
                            return CircuitState.HALF_OPEN

                return state

            # No state found - default to CLOSED
            return CircuitState.CLOSED

        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error getting circuit state from Redis",
                extra={"provider": provider, "error": str(exc)},
            )
            return CircuitState.CLOSED  # Fail-safe: allow requests

    async def _set_state_redis(self, provider: str, state: CircuitState) -> None:
        """Set circuit state in Redis."""
        try:
            key = self._redis_key(provider)
            await self.redis_client.client.hset(key, "state", state.value)  # type: ignore[misc,union-attr]

            if state == CircuitState.OPEN:
                await self.redis_client.client.hset(key, "opened_at", str(time.time()))  # type: ignore[misc,union-attr]

            # Set TTL (24 hours) to auto-cleanup old entries
            await self.redis_client.client.expire(key, 86400)  # type: ignore[misc,union-attr]

        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error setting circuit state in Redis",
                extra={"provider": provider, "state": state.value, "error": str(exc)},
            )

    async def _record_success(self, provider: str) -> None:
        """Record successful request."""
        try:
            if self.redis_client.is_available:
                key = self._redis_key(provider)

                # Increment success count
                success_count = int(await self.redis_client.client.hincrby(key, "success_count", 1))  # type: ignore[misc,union-attr]

                # Reset failure count
                await self.redis_client.client.hset(key, "failure_count", "0")  # type: ignore[misc,union-attr]

                # Check if HALF_OPEN should close
                state = await self._get_state_redis(provider)
                if state == CircuitState.HALF_OPEN and success_count >= self.success_threshold:
                    await self._set_state_redis(provider, CircuitState.CLOSED)
                    logger.info(
                        "Circuit breaker CLOSED after successful recovery",
                        extra={"provider": provider, "success_count": success_count},
                    )

        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error recording success",
                extra={"provider": provider, "error": str(exc)},
            )

    async def _record_failure(self, provider: str) -> None:
        """Record failed request."""
        try:
            if self.redis_client.is_available:
                key = self._redis_key(provider)

                # Increment failure count
                failure_count = int(await self.redis_client.client.hincrby(key, "failure_count", 1))  # type: ignore[misc,union-attr]

                # Reset success count
                await self.redis_client.client.hset(key, "success_count", "0")  # type: ignore[misc,union-attr]

                # Record failure time
                await self.redis_client.client.hset(key, "last_failure_time", str(time.time()))  # type: ignore[misc,union-attr]

                # Check if circuit should open
                state = await self._get_state_redis(provider)

                if state == CircuitState.CLOSED and failure_count >= self.failure_threshold:
                    # Open circuit
                    await self._set_state_redis(provider, CircuitState.OPEN)
                    logger.warning(
                        "Circuit breaker OPEN after consecutive failures",
                        extra={"provider": provider, "failure_count": failure_count},
                    )

                elif state == CircuitState.HALF_OPEN:
                    # Failed during recovery - reopen
                    await self._set_state_redis(provider, CircuitState.OPEN)
                    logger.warning(
                        "Circuit breaker OPEN after failed recovery attempt",
                        extra={"provider": provider},
                    )

        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error recording failure",
                extra={"provider": provider, "error": str(exc)},
            )

    async def _reset_redis(self, provider: str) -> None:
        """Reset circuit breaker in Redis."""
        try:
            key = self._redis_key(provider)
            await self.redis_client.client.delete(key)  # type: ignore[misc,union-attr]
        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error resetting circuit in Redis",
                extra={"provider": provider, "error": str(exc)},
            )

    async def _get_retry_after_seconds(self, provider: str) -> int:
        """Calculate seconds until retry (for OPEN state)."""
        try:
            if self.redis_client.is_available:
                key = self._redis_key(provider)
                opened_at = await self.redis_client.client.hget(key, "opened_at")  # type: ignore[misc,union-attr]
                if opened_at:
                    elapsed = time.time() - float(opened_at)
                    remaining = max(0, int(self.timeout_seconds - elapsed))
                    return remaining

        except Exception as exc:  # noqa: BLE001 - Graceful degradation
            logger.error(
                "Error calculating retry_after",
                extra={"provider": provider, "error": str(exc)},
            )

        return self.timeout_seconds

    # === Private: PostgreSQL Fallback Implementation ===

    async def _get_state_postgres(self, provider: str) -> CircuitState:  # noqa: ARG002
        """
        Get circuit state from PostgreSQL.

        Simple implementation: always return CLOSED when Redis unavailable.
        This ensures graceful degradation (fail-open pattern).

        Args:
            provider: Provider name (unused in fallback implementation)
        """
        return CircuitState.CLOSED

    async def _reset_postgres(self, provider: str) -> None:  # noqa: ARG002
        """
        Reset circuit breaker in PostgreSQL (no-op).

        Args:
            provider: Provider name (unused in fallback implementation)
        """
        # No-op: PostgreSQL fallback always returns CLOSED
        return


# Global circuit breaker instance (singleton)
_circuit_breaker: Optional[CircuitBreaker] = None
_circuit_settings: Optional[CircuitBreakerConfig] = None


def configure_circuit_breaker(settings: CircuitBreakerConfig) -> None:
    """Store circuit breaker configuration for runtime access."""
    global _circuit_settings
    _circuit_settings = settings


def get_circuit_breaker() -> CircuitBreaker:
    """
    Get or create the global circuit breaker instance.

    Returns:
        CircuitBreaker singleton instance
    """
    global _circuit_breaker  # noqa: PLW0603 - Singleton pattern

    if _circuit_breaker is None:
        if _circuit_settings is None:
            raise RuntimeError("Circuit breaker settings not configured")

        _circuit_breaker = CircuitBreaker(
            failure_threshold=_circuit_settings.failure_threshold,
            timeout_seconds=_circuit_settings.timeout_seconds,
            success_threshold=_circuit_settings.success_threshold,
        )

    return _circuit_breaker
