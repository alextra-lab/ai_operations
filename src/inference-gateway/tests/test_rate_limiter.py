"""
Unit tests for rate limiting service.

Tests:
- Token bucket algorithm
- Redis backend
- PostgreSQL fallback
- Configuration loading
- Multiple limit scopes
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared.auth.models import TokenPayload  # type: ignore

from app.services.rate_limiter import (
    PostgresRateLimiter,
    RateLimiter,
    RateLimitResult,
    TokenBucketLimiter,
)


def _make_redis_pipeline_mock(execute_result: list, zrange_result=None):
    """Build a Redis mock pipeline with execute()."""
    pipe = MagicMock()
    pipe.zremrangebyscore.return_value = pipe
    pipe.zcard.return_value = pipe
    pipe.execute = AsyncMock(return_value=execute_result)
    redis_mock = MagicMock()
    redis_mock.pipeline.return_value = pipe
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.zrange = AsyncMock(return_value=zrange_result if zrange_result is not None else [])
    return redis_mock, pipe


class TestTokenBucketLimiter:
    """Tests for Redis-backed token bucket limiter."""

    @pytest.mark.asyncio
    async def test_check_allowed_first_request(self):
        """Test that first request is allowed."""
        redis_mock, _ = _make_redis_pipeline_mock([None, 0])

        limiter = TokenBucketLimiter(redis_mock)

        allowed, retry_after, count = await limiter.check(
            key="ratelimit:test",
            limit=10,
            window_seconds=60,
            burst_size=2,
        )

        assert allowed is True
        assert retry_after == 0
        assert count == 1

    @pytest.mark.asyncio
    async def test_check_allowed_within_limit(self):
        """Test that requests within limit are allowed."""
        redis_mock, _ = _make_redis_pipeline_mock([None, 5])

        limiter = TokenBucketLimiter(redis_mock)

        allowed, retry_after, count = await limiter.check(
            key="ratelimit:test",
            limit=10,
            window_seconds=60,
            burst_size=2,
        )

        assert allowed is True
        assert retry_after == 0
        assert count == 6

    @pytest.mark.asyncio
    async def test_check_denied_at_limit(self):
        """Test that requests at limit are denied."""
        # Oldest entry in window: 30s ago so retry_after is ~31s
        import time

        oldest_ts = time.time() - 30
        redis_mock, _ = _make_redis_pipeline_mock([None, 12], zrange_result=[(b"req1", oldest_ts)])

        limiter = TokenBucketLimiter(redis_mock)

        allowed, retry_after, count = await limiter.check(
            key="ratelimit:test",
            limit=10,
            window_seconds=60,
            burst_size=2,
        )

        assert allowed is False
        assert retry_after > 0
        assert retry_after <= 60
        assert count == 12

    @pytest.mark.asyncio
    async def test_check_redis_error_raises(self):
        """Test that Redis errors are raised."""
        redis_mock = MagicMock()
        redis_mock.pipeline.side_effect = Exception("Redis connection failed")

        limiter = TokenBucketLimiter(redis_mock)

        with pytest.raises(Exception):
            await limiter.check(
                key="ratelimit:test",
                limit=10,
                window_seconds=60,
                burst_size=2,
            )


class TestPostgresRateLimiter:
    """Tests for PostgreSQL fallback limiter."""

    @pytest.mark.asyncio
    async def test_check_allowed_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = PostgresRateLimiter()

        # Mock database query to return count below limit
        with patch("app.services.rate_limiter.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (5,)  # 5 requests in window
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            allowed, retry_after, count = await limiter.check(
                key="ratelimit:test",
                limit=10,
                window_seconds=60,
                burst_size=2,
            )

            assert allowed is True
            assert retry_after == 0
            assert count == 5

    @pytest.mark.asyncio
    async def test_check_denied_at_limit(self):
        """Test that requests at limit are denied."""
        limiter = PostgresRateLimiter()

        # Mock database query to return count at limit
        with patch("app.services.rate_limiter.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (12,)  # 12 requests at limit
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            allowed, retry_after, count = await limiter.check(
                key="ratelimit:test",
                limit=10,
                window_seconds=60,
                burst_size=2,
            )

            assert allowed is False
            assert retry_after == 60
            assert count == 12

    @pytest.mark.asyncio
    async def test_check_database_error_fails_open(self):
        """Test that database errors fail open (allow request)."""
        limiter = PostgresRateLimiter()

        # Mock database error
        with patch("app.services.rate_limiter.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            allowed, retry_after, count = await limiter.check(
                key="ratelimit:test",
                limit=10,
                window_seconds=60,
                burst_size=2,
            )

            # Fail open
            assert allowed is True
            assert retry_after == 0
            assert count == 0


class TestRateLimiter:
    """Tests for rate limiter facade."""

    @pytest.mark.asyncio
    async def test_check_limit_disabled(self):
        """Test that rate limiting can be disabled."""
        limiter = RateLimiter(enable_rate_limiting=False)

        token = TokenPayload(
            sub="user-123",
            user_id="user-123",
            roles=["user"],
            exp=0,
            iat=0,
            iss="test",
            token_type="access",
        )

        result = await limiter.check_limit("global", token)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_limit_no_config(self):
        """Test that requests are allowed when no limit configured."""
        limiter = RateLimiter(enable_rate_limiting=True)

        # Mock database to return no configuration
        with patch.object(limiter, "_get_rate_limit_config", return_value=None):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_limit("global", token)

            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_limit_config_disabled(self):
        """Test that requests are allowed when limit is disabled."""
        limiter = RateLimiter(enable_rate_limiting=True)

        # Mock database to return disabled configuration
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={"enabled": False, "requests_per_minute": 100},
        ):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_limit("global", token)

            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_limit_global_allowed(self):
        """Test that global limit allows request within limit."""
        redis_mock, _ = _make_redis_pipeline_mock([None, 10])

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Mock configuration
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 100,
                "tokens_per_minute": None,
                "burst_size": 10,
            },
        ):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_limit("global", token)

            assert result.allowed is True
            assert result.limit_type == "global"

    @pytest.mark.asyncio
    async def test_check_limit_provider_denied(self):
        """Test that provider limit denies request when limit exceeded."""
        import time

        oldest_ts = time.time() - 15
        redis_mock, _ = _make_redis_pipeline_mock([None, 470], zrange_result=[(b"req1", oldest_ts)])

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Config: effective_limit = 450 + 20 = 470; count 470 is denied
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 450,
                "tokens_per_minute": 180000,
                "burst_size": 20,
            },
        ):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_limit(
                "provider",
                token,
                provider="openai",
            )

            assert result.allowed is False
            assert result.limit_type == "provider"
            assert result.identifier == "openai"
            assert result.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def test_check_limit_integration_service_account(self):
        """Test that integration limits apply to service accounts."""
        redis_mock, _ = _make_redis_pipeline_mock([None, 50])

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Mock configuration
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 100,
                "tokens_per_minute": None,
                "burst_size": 10,
            },
        ):
            token = TokenPayload(
                sub="cortex-prod",
                user_id="cortex-prod",
                roles=["service"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_limit("integration", token)

            assert result.allowed is True
            assert result.limit_type == "integration"
            assert result.identifier == "service:cortex-prod"

    @pytest.mark.asyncio
    async def test_check_all_limits_passes_all(self):
        """Test that check_all_limits passes when all limits allow."""
        redis_mock, _ = _make_redis_pipeline_mock([None, 10])

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Mock configuration to return enabled limits
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 100,
                "tokens_per_minute": None,
                "burst_size": 10,
            },
        ):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_all_limits(
                token=token,
                model="gpt-4o-mini",
                provider="openai",
            )

            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_all_limits_fails_global(self):
        """Test that check_all_limits fails when global limit exceeded."""
        redis_mock, _ = _make_redis_pipeline_mock(
            [None, 550], zrange_result=[(b"123.456", 123.456)]
        )

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Mock configuration
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 500,
                "tokens_per_minute": None,
                "burst_size": 50,
            },
        ):
            token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            result = await limiter.check_all_limits(
                token=token,
                model="gpt-4o-mini",
                provider="openai",
            )

            assert result.allowed is False
            assert result.limit_type == "global"

    @pytest.mark.asyncio
    async def test_redis_fallback_to_postgres(self):
        """Test that system falls back to PostgreSQL when Redis fails."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        redis_mock = MagicMock()
        redis_mock.pipeline.side_effect = RedisConnectionError("Redis connection failed")

        limiter = RateLimiter(redis_client=redis_mock, enable_rate_limiting=True)

        # Mock configuration
        with patch.object(
            limiter,
            "_get_rate_limit_config",
            return_value={
                "enabled": True,
                "requests_per_minute": 100,
                "tokens_per_minute": None,
                "burst_size": 10,
            },
        ):
            # Mock PostgreSQL to succeed
            with patch("app.services.rate_limiter.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_result = MagicMock()
                mock_result.fetchone.return_value = (10,)
                mock_db.execute = AsyncMock(return_value=mock_result)
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_get_db.return_value = mock_cm

                token = TokenPayload(
                    sub="user-123",
                    user_id="user-123",
                    roles=["user"],
                    exp=0,
                    iat=0,
                    iss="test",
                    token_type="access",
                )

                result = await limiter.check_limit("global", token)

                # Should fall back to PostgreSQL and succeed
                assert result.allowed is True


class TestRateLimitResult:
    """Tests for RateLimitResult model."""

    def test_allowed_result(self):
        """Test that allowed result is created correctly."""
        result = RateLimitResult(
            allowed=True,
            limit_type="global",
            current_count=50,
            limit=100,
        )

        assert result.allowed is True
        assert result.retry_after_seconds == 0
        assert result.limit_type == "global"
        assert result.current_count == 50
        assert result.limit == 100

    def test_denied_result(self):
        """Test that denied result is created correctly."""
        result = RateLimitResult(
            allowed=False,
            retry_after_seconds=30,
            limit_type="provider",
            identifier="openai",
            current_count=450,
            limit=450,
        )

        assert result.allowed is False
        assert result.retry_after_seconds == 30
        assert result.limit_type == "provider"
        assert result.identifier == "openai"
        assert result.current_count == 450
        assert result.limit == 450
