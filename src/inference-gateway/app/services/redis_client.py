"""
Redis client service for Inference Gateway.

Provides connection management with:
- Async connection pooling
- Health checking
- Graceful degradation if unavailable
- Automatic reconnection on failure

Used by:
- P2-T5: Rate limiting (token bucket counters)
- P2-T6: Circuit breaker (provider health state)

VERIFICATION:
- Uses redis.asyncio (async/await pattern)
- Connection pooling via from_url (reuses connections)
- Graceful fallback to PostgreSQL if unavailable
- Follows existing logging pattern (shared.logging_utils)
"""

from typing import Optional

import redis.asyncio as redis  # type: ignore[import-untyped]
from redis.asyncio import ConnectionPool  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError as RedisConnectionError  # type: ignore[import-untyped]
from redis.exceptions import RedisError  # type: ignore[import-untyped]
from redis.exceptions import TimeoutError as RedisTimeoutError  # type: ignore[import-untyped]
from shared.config.schemas import RedisConfig
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

logger = configure_logging(service_name="redis_client")


class RedisClient:
    """
    Redis connection manager with connection pooling and health checking.

    Features:
    - Async connection pool for efficiency
    - Health check via PING
    - Graceful degradation if unavailable
    - Automatic connection on first use

    Example:
        >>> redis_client = RedisClient(url="redis://localhost:6379")
        >>> await redis_client.connect()
        >>> if redis_client.is_available:
        ...     await redis_client.client.set("key", "value")
    """

    def __init__(
        self,
        url: str,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        """
        Initialize Redis client configuration.

        Args:
            url: Redis connection URL (redis://host:port/db)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
        """
        self.url = url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout

        # Connection state
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self._is_available = False

        logger.info(
            "Redis client initialized",
            extra={
                "max_connections": max_connections,
                "socket_timeout": socket_timeout,
            },
        )

    async def connect(self) -> bool:
        """
        Connect to Redis and verify availability.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )

            # Create Redis client from pool
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection with PING
            await self.client.ping()  # type: ignore[misc,union-attr]

            self._is_available = True
            logger.info("Redis connected successfully")
            return True

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                "Redis connection failed - will fallback to PostgreSQL",
                extra={"error_type": type(e).__name__},
            )
            self.client = None
            self.pool = None
            self._is_available = False
            return False

        except RedisError as e:
            logger.error(
                "Redis error during connection",
                extra={"error_type": type(e).__name__},
            )
            self.client = None
            self.pool = None
            self._is_available = False
            return False

        except Exception as e:
            logger.error(
                "Unexpected error connecting to Redis",
                extra={"error_type": type(e).__name__},
            )
            self.client = None
            self.pool = None
            self._is_available = False
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from Redis and close connection pool.

        Gracefully closes all connections in the pool.
        """
        if self.client is not None:
            try:
                await self.client.aclose()  # type: ignore[attr-defined]
                logger.info("Redis client closed")
            except Exception as e:
                logger.error("Error closing Redis client", extra={"error": str(e)})
            finally:
                self.client = None

        if self.pool is not None:
            try:
                await self.pool.aclose()  # type: ignore[attr-defined]
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error("Error closing Redis connection pool", extra={"error": str(e)})
            finally:
                self.pool = None

        self._is_available = False

    @property
    def is_available(self) -> bool:
        """
        Check if Redis is available for use.

        Returns:
            True if connected and healthy, False otherwise
        """
        return self._is_available and self.client is not None

    async def health_check(self) -> dict[str, str | bool]:
        """
        Perform health check on Redis connection.

        Returns:
            Dictionary with health status
        """
        if not self.is_available:
            return {
                "status": "unavailable",
                "connected": False,
                "message": "Redis not connected",
            }

        try:
            # Test with PING
            await self.client.ping()  # type: ignore[misc,union-attr]
            return {
                "status": "healthy",
                "connected": True,
                "message": "Redis responding to PING",
            }

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning("Redis health check failed", extra={"error": str(e)})
            self._is_available = False
            return {
                "status": "unhealthy",
                "connected": False,
                "message": f"Redis connection lost: {str(e)}",
            }

        except RedisError as e:
            logger.error("Redis error during health check", extra={"error": str(e)})
            return {
                "status": "error",
                "connected": True,
                "message": f"Redis error: {str(e)}",
            }

    async def get_info(self) -> dict[str, str | int | bool]:
        """
        Get Redis server information and statistics.

        Returns:
            Dictionary with Redis info (if available)
        """
        if not self.is_available:
            return {
                "available": False,
                "message": "Redis not available",
            }

        try:
            info = await self.client.info()  # type: ignore[misc,union-attr]
            return {
                "available": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }

        except Exception as e:
            logger.error("Error getting Redis info", extra={"error": str(e)})
            return {
                "available": False,
                "message": f"Error: {str(e)}",
            }


# Global Redis client instance (singleton pattern)
_redis_client: Optional[RedisClient] = None
_redis_settings: Optional[RedisConfig] = None


def configure_redis(settings: RedisConfig) -> None:
    """Configure Redis client settings."""
    global _redis_settings
    _redis_settings = settings


def get_redis_client() -> RedisClient:
    """
    Get or create the global Redis client instance.

    Returns:
        RedisClient singleton instance
    """
    global _redis_client

    if _redis_client is None:
        if _redis_settings is None:
            raise RuntimeError("Redis settings not configured")

        _redis_client = RedisClient(
            url=_redis_settings.url,
            max_connections=_redis_settings.max_connections,
            socket_timeout=_redis_settings.socket_timeout,
            socket_connect_timeout=_redis_settings.socket_connect_timeout,
        )

    return _redis_client


async def init_redis(redis_settings: RedisConfig) -> RedisClient:
    """
    Initialize Redis client and connect.

    Called during application startup.

    Returns:
        RedisClient instance (connected or not)
    """
    configure_redis(redis_settings)

    if not redis_settings.enabled:
        logger.info("Redis disabled via configuration")
        return get_redis_client()

    client = get_redis_client()
    await client.connect()

    if not client.is_available:
        logger.warning("Redis unavailable - rate limiting will fall back to PostgreSQL")

    return client


async def shutdown_redis() -> None:
    """
    Shutdown Redis client and close connections.

    Called during application shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.disconnect()
        _redis_client = None
