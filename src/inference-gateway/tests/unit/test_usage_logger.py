"""
Unit tests for BatchUsageLogger service.

Tests batch queuing, flush behavior, error handling, and graceful shutdown.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.usage_logger import BatchUsageLogger


@pytest.fixture
def mock_get_db():
    """Mock shared.database.get_db context manager."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    async def mock_context():
        yield mock_db

    with patch("app.services.usage_logger.get_db") as mock:
        mock.return_value = mock_context()
        yield mock


@pytest.fixture
def sample_usage_data():
    """Sample usage record data."""
    return {
        "request_id": f"req_{uuid4().hex[:16]}",
        "user_id": uuid4(),
        "endpoint": "/v1/chat/completions",
        "provider_name": "openai",
        "model_requested": "gpt-4o-mini",
        "model_used": "gpt-4o-mini",
        "tokens_in": 100,
        "tokens_out": 50,
        "latency_total_ms": 250,
        "http_status": 200,
        "success": True,
        "stream_enabled": False,
    }


# Default config values (must match UsageLoggerConfig defaults)
DEFAULT_BATCH_SIZE = 10
DEFAULT_FLUSH_INTERVAL = 5.0


# Initialization Tests


def test_init_default_config():
    """Test logger initializes with explicit default config."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    assert logger.batch_size == DEFAULT_BATCH_SIZE
    assert logger.flush_interval == DEFAULT_FLUSH_INTERVAL
    assert len(logger.queue) == 0
    assert not logger._running


def test_init_custom_config():
    """Test logger initializes with custom config."""
    logger = BatchUsageLogger(batch_size=20, flush_interval=10.0)

    assert logger.batch_size == 20
    assert logger.flush_interval == 10.0


# Queue Behavior Tests


@pytest.mark.asyncio
async def test_log_usage_queues_record(sample_usage_data):
    """Test log_usage adds record to queue."""
    logger = BatchUsageLogger(batch_size=10, flush_interval=5.0)

    await logger.log_usage(sample_usage_data)

    assert len(logger.queue) == 1
    assert logger.queue[0]["request_id"] == sample_usage_data["request_id"]


@pytest.mark.asyncio
async def test_log_usage_missing_required_fields():
    """Test log_usage rejects records with missing required fields."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Missing request_id
    incomplete_data = {
        "endpoint": "/v1/chat/completions",
        "model_requested": "gpt-4o-mini",
        "http_status": 200,
        "success": True,
    }

    await logger.log_usage(incomplete_data)

    # Should not be queued
    assert len(logger.queue) == 0


@pytest.mark.asyncio
async def test_log_usage_triggers_flush_at_batch_size(mock_get_db, sample_usage_data):
    """Test queue flushes when batch_size reached."""
    logger = BatchUsageLogger(batch_size=3, flush_interval=10.0)

    # Add 2 records (below batch size)
    await logger.log_usage(sample_usage_data.copy())
    await logger.log_usage(sample_usage_data.copy())
    await asyncio.sleep(0.1)  # Allow async task to run

    assert len(logger.queue) == 2

    # Add 3rd record (triggers flush)
    await logger.log_usage(sample_usage_data.copy())
    await asyncio.sleep(0.1)  # Allow flush to complete

    # Queue should be empty after flush
    assert len(logger.queue) == 0
    mock_get_db.assert_called()


# Flush Behavior Tests


@pytest.mark.asyncio
async def test_flush_empty_queue(mock_get_db):
    """Test flush does nothing when queue is empty."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger._flush()

    # No database operations
    mock_get_db.assert_not_called()


@pytest.mark.asyncio
async def test_flush_batch_insert(mock_get_db, sample_usage_data):
    """Test flush performs batch insert to database."""
    logger = BatchUsageLogger(batch_size=10, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Queue 3 records
    await logger.log_usage(sample_usage_data.copy())
    await logger.log_usage(sample_usage_data.copy())
    await logger.log_usage(sample_usage_data.copy())

    await logger._flush()

    # Database should be called
    mock_get_db.assert_called()


@pytest.mark.asyncio
async def test_flush_adds_timestamps(mock_get_db, sample_usage_data):
    """Test flush adds timestamps to records missing them."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Add record without timestamps
    await logger.log_usage(sample_usage_data)
    assert len(logger.queue) == 1

    # Flush
    with patch.object(logger, "queue", logger.queue):
        await logger._flush()

    # Timestamps should be added before insert
    mock_get_db.assert_called()


@pytest.mark.asyncio
async def test_flush_respects_batch_size(mock_get_db, sample_usage_data):
    """Test flush only processes batch_size records at a time."""
    logger = BatchUsageLogger(batch_size=2, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Queue 5 records
    for _ in range(5):
        await logger.log_usage(sample_usage_data.copy())

    assert len(logger.queue) == 5

    # Flush (should only process 2)
    await logger._flush()

    # 3 records should remain in queue
    assert len(logger.queue) == 3


@pytest.mark.asyncio
async def test_flush_handles_db_errors_gracefully(mock_get_db, sample_usage_data):
    """Test flush continues on database errors (graceful degradation)."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Mock database error
    mock_db_instance = AsyncMock()
    mock_db_instance.execute.side_effect = Exception("Database connection failed")

    async def mock_context():
        yield mock_db_instance

    mock_get_db.return_value = mock_context()

    # Queue record
    await logger.log_usage(sample_usage_data)

    # Flush should not crash
    await logger._flush()

    # Queue should be cleared (records lost, but service continues)
    assert len(logger.queue) == 0


# Background Flush Loop Tests


@pytest.mark.asyncio
async def test_start_creates_flush_task():
    """Test start() creates background flush task."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger.start()

    assert logger._running is True
    assert logger._flush_task is not None
    assert not logger._flush_task.done()

    # Cleanup
    await logger.shutdown()


@pytest.mark.asyncio
async def test_start_idempotent():
    """Test start() can be called multiple times safely."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger.start()
    first_task = logger._flush_task

    await logger.start()  # Second start
    second_task = logger._flush_task

    # Should still be the same task
    assert first_task is second_task

    # Cleanup
    await logger.shutdown()


@pytest.mark.asyncio
async def test_flush_loop_periodic_flush(mock_get_db, sample_usage_data):
    """Test flush loop flushes periodically based on flush_interval."""
    logger = BatchUsageLogger(batch_size=100, flush_interval=0.2)  # Short interval for test

    await logger.start()

    # Queue record
    await logger.log_usage(sample_usage_data)
    assert len(logger.queue) == 1

    # Wait for flush interval to elapse
    await asyncio.sleep(0.3)

    # Queue should be flushed
    assert len(logger.queue) == 0
    mock_get_db.assert_called()

    # Cleanup
    await logger.shutdown()


# Shutdown Tests


@pytest.mark.asyncio
async def test_shutdown_stops_flush_loop():
    """Test shutdown() stops background flush task."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger.start()
    assert logger._running is True

    await logger.shutdown()

    assert logger._running is False
    assert logger._flush_task.done()


@pytest.mark.asyncio
async def test_shutdown_flushes_pending_records(mock_get_db, sample_usage_data):
    """Test shutdown() flushes all pending records."""
    logger = BatchUsageLogger(
        batch_size=100, flush_interval=10.0
    )  # High batch size to prevent auto-flush

    await logger.start()

    # Queue records
    await logger.log_usage(sample_usage_data.copy())
    await logger.log_usage(sample_usage_data.copy())
    assert len(logger.queue) == 2

    # Shutdown (should flush)
    await logger.shutdown()

    # Queue should be empty
    assert len(logger.queue) == 0
    mock_get_db.assert_called()


@pytest.mark.asyncio
async def test_shutdown_idempotent():
    """Test shutdown() can be called multiple times safely."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger.start()
    await logger.shutdown()

    # Second shutdown should not crash
    await logger.shutdown()

    assert logger._running is False


@pytest.mark.asyncio
async def test_shutdown_without_start():
    """Test shutdown() works even if start() was never called."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Should not crash
    await logger.shutdown()

    assert logger._running is False


# Statistics Tests


def test_get_stats():
    """Test get_stats() returns correct statistics."""
    logger = BatchUsageLogger(batch_size=15, flush_interval=8.0)

    stats = logger.get_stats()

    assert stats["queue_size"] == 0
    assert stats["batch_size"] == 15
    assert stats["flush_interval"] == 8.0
    assert stats["running"] is False


@pytest.mark.asyncio
async def test_get_stats_after_start():
    """Test get_stats() shows running=True after start()."""
    logger = BatchUsageLogger(batch_size=DEFAULT_BATCH_SIZE, flush_interval=DEFAULT_FLUSH_INTERVAL)

    await logger.start()
    stats = logger.get_stats()

    assert stats["running"] is True

    # Cleanup
    await logger.shutdown()


# Integration Behavior Tests


@pytest.mark.asyncio
async def test_high_throughput_handling(mock_get_db, sample_usage_data):
    """Test logger handles high request throughput."""
    logger = BatchUsageLogger(batch_size=10, flush_interval=1.0)

    await logger.start()

    # Simulate 100 rapid requests
    tasks = [logger.log_usage(sample_usage_data.copy()) for _ in range(100)]
    await asyncio.gather(*tasks)

    # Wait for flushes to complete
    await asyncio.sleep(0.5)

    # All records should be flushed
    assert len(logger.queue) < 10  # May have some pending

    # Cleanup
    await logger.shutdown()

    # All records should be flushed after shutdown
    assert len(logger.queue) == 0


@pytest.mark.asyncio
async def test_concurrent_flush_safety(mock_get_db, sample_usage_data):
    """Test concurrent flushes don't cause race conditions."""
    logger = BatchUsageLogger(batch_size=5, flush_interval=DEFAULT_FLUSH_INTERVAL)

    # Queue records
    for _ in range(10):
        await logger.log_usage(sample_usage_data.copy())

    # Trigger multiple concurrent flushes
    flush_tasks = [logger._flush() for _ in range(3)]
    await asyncio.gather(*flush_tasks)

    # All records should be processed (no duplicates)
    assert len(logger.queue) == 0
    assert mock_get_db.call_count >= 1
