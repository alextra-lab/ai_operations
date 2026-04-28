"""Unit tests for WebSocket router."""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.routers.websocket import (  # type: ignore[import]
    _get_cpu_usage,
    _get_memory_usage,
    dashboard_websocket,
    generate_dashboard_data,
    router,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_router_fixture():
    """Create FastAPI app with WebSocket router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app_with_router_fixture):
    """Create test client."""
    return TestClient(app_with_router_fixture)


def test_generate_dashboard_data():
    """Test that dashboard data is generated correctly."""
    data = generate_dashboard_data()

    assert data["type"] == "dashboard_data"
    assert "data" in data
    assert "timestamp" in data["data"]
    assert "system_health" in data["data"]
    assert "threat_events" in data["data"]
    assert "security_alerts" in data["data"]
    assert "user_activity" in data["data"]
    assert "query_stats" in data["data"]
    assert "performance_metrics" in data["data"]
    assert "document_processing" in data["data"]

    # Validate system_health structure (real service health checks)
    system_health = data["data"]["system_health"]
    assert "status" in system_health
    assert "uptime" in system_health
    assert "services" in system_health
    assert "last_check" in system_health
    # At minimum, PostgreSQL is always checked
    assert len(system_health["services"]) >= 1

    # Validate threat_events structure
    threat_events = data["data"]["threat_events"]
    assert isinstance(threat_events, list)
    assert len(threat_events) >= 5
    event = threat_events[0]
    assert "id" in event
    assert "title" in event
    assert "severity" in event

    alerts = data["data"]["security_alerts"]
    assert isinstance(alerts, list)
    assert len(alerts) >= 3

    activities = data["data"]["user_activity"]
    assert isinstance(activities, list)
    assert len(activities) >= 5

    # Validate performance_metrics has real metrics
    perf = data["data"]["performance_metrics"]
    assert "cpu_usage" in perf
    assert "memory_usage" in perf
    assert "active_connections" in perf
    assert isinstance(perf["cpu_usage"], int | float)
    assert isinstance(perf["memory_usage"], int | float)

    stats = data["data"]["query_stats"]
    assert len(stats["top_queries"]) == 5
    assert len(stats["recent_queries"]) == 10

    docs = data["data"]["document_processing"]["recent_documents"]
    assert len(docs) == 5


def test_get_cpu_usage_reads_proc_stat(monkeypatch):
    """CPU usage should be derived from /proc/stat contents."""
    sample_stat = "cpu  10 0 10 20 0 0 0 0 0 0\n"

    def fake_exists(_path: Path):
        return str(_path) == "/proc/stat"

    def fake_open(_path: Path, *_args, **_kwargs):
        return StringIO(sample_stat)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "open", fake_open)

    assert _get_cpu_usage() == 50.0  # idle 20 of total 40 -> 50% usage


def test_get_memory_usage_reads_proc_meminfo(monkeypatch):
    """Memory usage should be derived from /proc/meminfo contents."""
    sample_meminfo = "MemTotal:       1000 kB\nMemAvailable:   250 kB\n"

    def fake_exists(_path: Path):
        return str(_path) == "/proc/meminfo"

    def fake_open(_path: Path, *_args, **_kwargs):
        return StringIO(sample_meminfo)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "open", fake_open)

    assert _get_memory_usage() == 75.0  # (1000-250)/1000


def test_generate_dashboard_data_includes_real_metrics(monkeypatch):
    """Dashboard data should surface real metrics fields."""

    # Avoid reading host /proc during test
    monkeypatch.setattr("app.routers.websocket._get_cpu_usage", lambda: 12.3)
    monkeypatch.setattr("app.routers.websocket._get_memory_usage", lambda: 34.5)

    data = generate_dashboard_data()
    perf = data["data"]["performance_metrics"]

    assert perf["cpu_usage"] == 12.3
    assert perf["memory_usage"] == 34.5
    assert "active_connections" in perf
    assert isinstance(perf["active_connections"], int)


@pytest.mark.asyncio
async def test_dashboard_websocket_accepts_connection():
    """Test that dashboard WebSocket accepts connections."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()

    # Simulate disconnect during accept
    async def mock_accept():
        raise WebSocketDisconnect(code=1000)

    websocket.accept.side_effect = mock_accept

    # Should handle disconnect gracefully
    await dashboard_websocket(websocket)

    websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_dashboard_websocket_sends_initial_data():
    """Test that dashboard WebSocket sends initial data."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()

    # Simulate disconnect after initial data is sent
    call_count = 0

    async def mock_send_text(_data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # After first message, raise disconnect in next sleep
            pass

    async def mock_sleep(_seconds):
        if call_count >= 1:
            raise WebSocketDisconnect(code=1000)

    websocket.send_text.side_effect = mock_send_text

    with patch("asyncio.sleep", side_effect=mock_sleep):
        await dashboard_websocket(websocket)

    # Verify initial data was sent
    assert websocket.send_text.call_count >= 1
    sent_data = json.loads(websocket.send_text.call_args_list[0][0][0])
    assert sent_data["type"] == "dashboard_data"


@pytest.mark.asyncio
async def test_dashboard_websocket_handles_disconnect():
    """Test that dashboard WebSocket handles disconnect gracefully."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000))
    websocket.close = AsyncMock()

    await dashboard_websocket(websocket)

    websocket.accept.assert_called_once()
    # Should not raise exception


@pytest.mark.asyncio
async def test_dashboard_websocket_handles_errors():
    """Test that dashboard WebSocket handles errors gracefully."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock(side_effect=RuntimeError("Test error"))
    websocket.close = AsyncMock()

    # Should handle error and close connection
    await dashboard_websocket(websocket)

    websocket.accept.assert_called_once()
    websocket.close.assert_called_once()


def test_websocket_route_registered(app_with_router_fixture):
    """Test that WebSocket route is registered."""
    routes = [route.path for route in app_with_router_fixture.routes]
    assert "/ws/dashboard" in routes
