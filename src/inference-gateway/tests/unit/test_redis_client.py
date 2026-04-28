"""
Unit tests for RedisClient service (P2-T4).

Tests:
- Connection establishment
- Health checking
- Graceful degradation on failure
- Connection pooling
- Singleton pattern
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from shared.config.schemas import RedisConfig

from app.services.redis_client import (
    RedisClient,
    configure_redis,
    get_redis_client,
    init_redis,
    shutdown_redis,
)


@pytest.fixture
def redis_url():
    """Redis test URL."""
    return "redis://localhost:6379"


@pytest.fixture
def redis_client(redis_url):
    """Create RedisClient instance for testing."""
    return RedisClient(url=redis_url)


class TestRedisClient:
    """Test suite for RedisClient class."""

    @pytest.mark.asyncio
    async def test_initialization(self, redis_client, redis_url):
        """Test RedisClient initialization with configuration."""
        assert redis_client.url == redis_url
        assert redis_client.max_connections == 50
        assert redis_client.socket_timeout == 5
        assert redis_client.socket_connect_timeout == 5
        assert redis_client.client is None
        assert redis_client.pool is None
        assert redis_client.is_available is False

    @pytest.mark.asyncio
    async def test_connect_success(self, redis_client):
        """Test successful Redis connection."""
        with (
            patch("app.services.redis_client.ConnectionPool.from_url") as mock_pool,
            patch("app.services.redis_client.redis.Redis") as mock_redis_class,
        ):
            # Mock connection pool
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            # Mock Redis client
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(return_value=True)
            mock_redis_class.return_value = mock_redis_instance

            # Connect
            result = await redis_client.connect()

            # Verify
            assert result is True
            assert redis_client.is_available is True
            assert redis_client.client is not None
            mock_redis_instance.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_connection_error(self, redis_client):
        """Test Redis connection failure with ConnectionError."""
        with (
            patch("app.services.redis_client.ConnectionPool.from_url") as mock_pool,
            patch("app.services.redis_client.redis.Redis") as mock_redis_class,
        ):
            # Mock connection pool
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            # Mock Redis client that raises ConnectionError on ping
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(
                side_effect=RedisConnectionError("Connection refused")
            )
            mock_redis_class.return_value = mock_redis_instance

            # Connect
            result = await redis_client.connect()

            # Verify graceful failure
            assert result is False
            assert redis_client.is_available is False
            assert redis_client.client is None
            assert redis_client.pool is None

    @pytest.mark.asyncio
    async def test_connect_failure_timeout_error(self, redis_client):
        """Test Redis connection failure with TimeoutError."""
        with (
            patch("app.services.redis_client.ConnectionPool.from_url") as mock_pool,
            patch("app.services.redis_client.redis.Redis") as mock_redis_class,
        ):
            # Mock connection pool
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            # Mock Redis client that times out
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(
                side_effect=RedisTimeoutError("Connection timeout")
            )
            mock_redis_class.return_value = mock_redis_instance

            # Connect
            result = await redis_client.connect()

            # Verify graceful failure
            assert result is False
            assert redis_client.is_available is False

    @pytest.mark.asyncio
    async def test_connect_failure_generic_exception(self, redis_client):
        """Test Redis connection failure with generic exception."""
        with patch("app.services.redis_client.ConnectionPool.from_url") as mock_pool:
            # Mock pool that raises generic exception
            mock_pool.side_effect = Exception("Unexpected error")

            # Connect
            result = await redis_client.connect()

            # Verify graceful failure
            assert result is False
            assert redis_client.is_available is False

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_client):
        """Test Redis disconnection."""
        # Mock client and pool
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        redis_client.client = mock_client

        mock_pool = AsyncMock()
        mock_pool.aclose = AsyncMock()
        redis_client.pool = mock_pool

        redis_client._is_available = True

        # Disconnect
        await redis_client.disconnect()

        # Verify
        mock_client.aclose.assert_called_once()
        mock_pool.aclose.assert_called_once()
        assert redis_client.client is None
        assert redis_client.pool is None
        assert redis_client.is_available is False

    @pytest.mark.asyncio
    async def test_health_check_when_unavailable(self, redis_client):
        """Test health check when Redis unavailable."""
        # Redis not connected
        redis_client._is_available = False

        # Health check
        health = await redis_client.health_check()

        # Verify
        assert health["status"] == "unavailable"
        assert health["connected"] is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, redis_client):
        """Test successful health check."""
        # Mock connected Redis
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        redis_client.client = mock_client
        redis_client._is_available = True

        # Health check
        health = await redis_client.health_check()

        # Verify
        assert health["status"] == "healthy"
        assert health["connected"] is True
        mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_connection_lost(self, redis_client):
        """Test health check when connection lost."""
        # Mock Redis that fails ping
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=RedisConnectionError("Connection lost"))
        redis_client.client = mock_client
        redis_client._is_available = True

        # Health check
        health = await redis_client.health_check()

        # Verify
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert redis_client.is_available is False  # Marked unavailable

    @pytest.mark.asyncio
    async def test_get_info_when_unavailable(self, redis_client):
        """Test get_info when Redis unavailable."""
        redis_client._is_available = False

        # Get info
        info = await redis_client.get_info()

        # Verify
        assert info["available"] is False
        assert "message" in info

    @pytest.mark.asyncio
    async def test_get_info_success(self, redis_client):
        """Test successful get_info."""
        # Mock Redis with info
        mock_client = AsyncMock()
        mock_client.info = AsyncMock(
            return_value={
                "redis_version": "7.0.0",
                "used_memory": 1024000,
                "connected_clients": 5,
                "total_connections_received": 100,
                "total_commands_processed": 500,
                "uptime_in_seconds": 3600,
            }
        )
        redis_client.client = mock_client
        redis_client._is_available = True

        # Get info
        info = await redis_client.get_info()

        # Verify
        assert info["available"] is True
        assert info["redis_version"] == "7.0.0"
        assert info["used_memory"] == 1024000
        assert info["connected_clients"] == 5


class TestRedisClientSingleton:
    """Test singleton pattern for global Redis client."""

    def test_get_redis_client_creates_instance(self):
        """Test get_redis_client creates singleton instance."""
        settings = RedisConfig(
            url="redis://test:6379",
            max_connections=25,
            socket_timeout=10,
            socket_connect_timeout=10,
        )
        with patch("app.services.redis_client._redis_client", None):
            configure_redis(settings)
            client = get_redis_client()

            # Verify instance created
            assert client is not None
            assert client.url == "redis://test:6379"
            assert client.max_connections == 25
            assert client.socket_timeout == 10

    def test_get_redis_client_returns_same_instance(self):
        """Test get_redis_client returns singleton."""
        with patch("app.services.redis_client._redis_client", None):
            client1 = get_redis_client()
            client2 = get_redis_client()

            # Same instance
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_init_redis_when_enabled(self):
        """Test init_redis when Redis enabled."""
        settings = RedisConfig(url="redis://localhost:6379", enabled=True)
        with (
            patch("app.services.redis_client._redis_client", None),
            patch("app.services.redis_client.ConnectionPool.from_url"),
            patch("app.services.redis_client.redis.Redis") as mock_redis_class,
        ):
            # Mock Redis client
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(return_value=True)
            mock_redis_class.return_value = mock_redis_instance

            # Initialize
            client = await init_redis(settings)

            # Verify connection attempted
            assert client is not None
            mock_redis_instance.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_redis_when_disabled(self):
        """Test init_redis when Redis disabled."""
        settings = RedisConfig(url="redis://localhost:6379", enabled=False)
        with patch("app.services.redis_client._redis_client", None):
            # Initialize
            client = await init_redis(settings)

            # Verify client created but not connected
            assert client is not None
            assert client.is_available is False

    @pytest.mark.asyncio
    async def test_shutdown_redis(self):
        """Test shutdown_redis clears singleton."""
        with patch("app.services.redis_client._redis_client", None):
            # Create client
            client = get_redis_client()
            client.disconnect = AsyncMock()

            # Shutdown
            await shutdown_redis()

            # Verify disconnect called and singleton cleared
            client.disconnect.assert_called_once()


class TestRedisClientIntegration:
    """Integration-style tests (with mocks but realistic flows)."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full Redis client lifecycle."""
        settings = RedisConfig(url="redis://localhost:6379", enabled=True)
        with (
            patch("app.services.redis_client._redis_client", None),
            patch("app.services.redis_client.ConnectionPool.from_url"),
            patch("app.services.redis_client.redis.Redis") as mock_redis_class,
        ):
            # Mock Redis client
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(return_value=True)
            mock_redis_instance.info = AsyncMock(return_value={"redis_version": "7.0.0"})
            mock_redis_instance.aclose = AsyncMock()
            mock_redis_class.return_value = mock_redis_instance

            # Initialize
            client = await init_redis(settings)
            assert client.is_available

            # Health check
            health = await client.health_check()
            assert health["status"] == "healthy"

            # Get info
            info = await client.get_info()
            assert info["available"] is True

            # Shutdown
            await shutdown_redis()

    @pytest.mark.asyncio
    async def test_fallback_on_connection_failure(self):
        """Test graceful fallback when Redis unavailable."""
        settings = RedisConfig(url="redis://localhost:6379", enabled=True)
        with (
            patch("app.services.redis_client._redis_client", None),
            patch(
                "app.services.redis_client.ConnectionPool.from_url",
                side_effect=RedisConnectionError("Connection refused"),
            ),
        ):
            # Initialize
            client = await init_redis(settings)

            # Verify graceful fallback
            assert client is not None
            assert not client.is_available

            # Health check should work even when unavailable
            health = await client.health_check()
            assert health["status"] == "unavailable"
