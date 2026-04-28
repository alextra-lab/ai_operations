"""
Batch Usage Logger for Inference Gateway.

Async non-blocking queue with batch insert for performance.

VERIFICATION CRITICAL:
- Uses shared.database.get_db (DON'T create new connection pool)
- Async background task (DON'T block request handling)
- Configurable via env vars (existing pattern)
- Follows ADR-053 (Rate Limiting and Usage Tracking)
"""

import asyncio
from collections import deque
from datetime import UTC, datetime
from typing import Any

from shared.config.schemas import UsageLoggerConfig
from shared.database import get_db  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from sqlalchemy import insert

from ..database.usage import GatewayUsageLog

logger = configure_logging(service_name="usage_logger")


class BatchUsageLogger:
    """
    Batch insert usage records to reduce DB overhead.

    Features:
    - Async non-blocking queue (doesn't slow requests)
    - Configurable batch size and flush interval
    - Graceful shutdown (flushes all pending records)
    - Uses existing shared.database.get_db pattern

    Example:
        >>> logger = BatchUsageLogger(batch_size=10, flush_interval=5.0)
        >>> await logger.start()  # Start background flush task
        >>> await logger.log_usage({...})  # Queue usage record
        >>> await logger.shutdown()  # Flush and stop
    """

    def __init__(
        self,
        batch_size: int,
        flush_interval: float,
    ):
        """
        Initialize batch logger.

        Args:
            batch_size: Records per batch (default: 10 from env GATEWAY_USAGE_BATCH_SIZE)
            flush_interval: Seconds between flushes (default: 5.0 from env GATEWAY_USAGE_FLUSH_INTERVAL)
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: deque[dict[str, Any]] = deque()
        self._flush_task: asyncio.Task | None = None
        self._running = False
        self._shutdown_event = asyncio.Event()

        logger.info(
            "BatchUsageLogger initialized",
            extra={
                "batch_size": self.batch_size,
                "flush_interval": self.flush_interval,
            },
        )

    async def start(self) -> None:
        """
        Start background flush task.

        Should be called on app startup.
        """
        if self._running:
            logger.warning("BatchUsageLogger already running")
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("BatchUsageLogger started")

    async def shutdown(self) -> None:
        """
        Graceful shutdown - flush all pending records.

        Should be called on app shutdown.
        """
        if not self._running:
            return

        logger.info("BatchUsageLogger shutting down", extra={"pending_records": len(self.queue)})

        self._running = False
        self._shutdown_event.set()

        # Wait for flush task to complete
        if self._flush_task:
            await self._flush_task

        # Final flush of any remaining records
        if self.queue:
            await self._flush()

        logger.info("BatchUsageLogger shutdown complete")

    async def log_usage(self, usage_data: dict[str, Any]) -> None:
        """
        Queue usage record (async, non-blocking).

        Args:
            usage_data: Usage record data matching GatewayUsageLog columns

        Note:
            This method returns immediately. Records are batched and flushed
            asynchronously to minimize request latency impact.
        """
        # Validate required fields (fail fast if misconfigured)
        required_fields = [
            "request_id",
            "endpoint",
            "model_requested",
            "http_status",
            "success",
        ]
        missing = [f for f in required_fields if f not in usage_data]
        if missing:
            logger.error(
                "Missing required fields in usage data",
                extra={
                    "missing_fields": missing,
                    "request_id": usage_data.get("request_id"),
                },
            )
            return

        self.queue.append(usage_data)
        logger.debug(
            "Usage record queued",
            extra={
                "queue_size": len(self.queue),
                "request_id": usage_data.get("request_id"),
            },
        )

        # Flush immediately if batch size reached
        if len(self.queue) >= self.batch_size:
            # Don't await - fire and forget for performance
            asyncio.create_task(self._flush())

    async def _flush_loop(self) -> None:
        """
        Background task that flushes queue periodically.

        Runs until shutdown signal received.
        """
        logger.info("Flush loop started", extra={"flush_interval": self.flush_interval})

        while self._running:
            try:
                # Wait for flush interval or shutdown signal
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.flush_interval)
                # Shutdown signal received
                break
            except asyncio.TimeoutError:
                # Flush interval elapsed
                if self.queue:
                    await self._flush()

        logger.info("Flush loop stopped")

    async def _flush(self) -> None:
        """
        Batch insert queued records to database.

        Handles errors gracefully (logs but doesn't crash).
        """
        if not self.queue:
            return

        # Move records from queue to batch
        batch: list[dict[str, Any]] = []
        while self.queue and len(batch) < self.batch_size:
            batch.append(self.queue.popleft())

        if not batch:
            return

        # Add timestamps if missing
        now = datetime.now(tz=UTC)
        for record in batch:
            if "ts_utc" not in record:
                record["ts_utc"] = now
            if "created_at" not in record:
                record["created_at"] = now
            # Ensure metadata_json exists
            if "metadata_json" not in record:
                record["metadata_json"] = {}

        try:
            async with get_db() as db:
                # Bulk insert using SQLAlchemy Core (efficient)
                stmt = insert(GatewayUsageLog).values(batch)
                await db.execute(stmt)
                await db.commit()

            logger.info(
                "Flushed usage records",
                extra={
                    "records_flushed": len(batch),
                    "queue_remaining": len(self.queue),
                },
            )

        except Exception as e:
            logger.exception(
                "Error flushing usage records",
                extra={
                    "error": str(e),
                    "records_lost": len(batch),
                    "queue_remaining": len(self.queue),
                },
            )
            # Don't re-queue failed records to avoid infinite growth
            # Log error and continue (graceful degradation)

    def get_stats(self) -> dict[str, Any]:
        """
        Get current logger statistics.

        Returns:
            dict with queue_size, batch_size, flush_interval, running
        """
        return {
            "queue_size": len(self.queue),
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
            "running": self._running,
        }


# Global singleton instance
# Initialized at module level for use across routers
_usage_logger: BatchUsageLogger | None = None


def get_usage_logger() -> BatchUsageLogger:
    """
    Get global usage logger instance.

    Returns:
        BatchUsageLogger: Global singleton instance

    Raises:
        RuntimeError: If logger not initialized (call init_usage_logger first)
    """
    global _usage_logger
    if _usage_logger is None:
        raise RuntimeError("Usage logger not initialized. Call init_usage_logger() first.")
    return _usage_logger


def init_usage_logger(settings: UsageLoggerConfig) -> BatchUsageLogger:
    """
    Initialize global usage logger.

    Should be called on app startup (main.py).

    Args:
        batch_size: Records per batch (default from env)
        flush_interval: Seconds between flushes (default from env)

    Returns:
        BatchUsageLogger: Initialized global instance
    """
    global _usage_logger
    if _usage_logger is not None:
        logger.warning("Usage logger already initialized")
        return _usage_logger

    _usage_logger = BatchUsageLogger(
        batch_size=settings.batch_size,
        flush_interval=settings.flush_interval_seconds,
    )
    return _usage_logger
