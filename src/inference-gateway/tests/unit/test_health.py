"""
Unit tests for health check endpoint.

Tests the basic health endpoint functionality.

Note: The lifespan calls init_db() and check_database_connection() on startup.
We mock these at the fixture level to avoid requiring a real database connection
during test client creation.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create test client for FastAPI app.

    Mocks database initialization functions to avoid requiring a real
    database connection during lifespan startup.
    """
    with (
        patch("app.database.connection.init_db", new_callable=AsyncMock) as mock_init,
        patch(
            "app.database.connection.check_database_connection",
            new_callable=AsyncMock,
        ) as mock_check,
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.check_database_connection", new_callable=AsyncMock),
    ):
        # Default: database is healthy during startup
        mock_init.return_value = None
        mock_check.return_value = True

        from app.main import app

        yield TestClient(app)


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Test that health endpoint returns 200 OK when database is healthy."""
    with patch("app.main.check_database_connection", new_callable=AsyncMock) as mock_db_check:
        mock_db_check.return_value = True

        response = client.get("/health")
        assert response.status_code == 200


def test_health_endpoint_returns_correct_structure(client: TestClient) -> None:
    """Test that health endpoint returns expected JSON structure."""
    with patch("app.main.check_database_connection", new_callable=AsyncMock) as mock_db_check:
        mock_db_check.return_value = True

        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "dependencies" in data

        assert data["status"] == "healthy"
        assert data["service"] == "inference-gateway"
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]


def test_health_endpoint_returns_503_when_db_unhealthy(
    client: TestClient,
) -> None:
    """Test that health endpoint returns 503 when database is unhealthy."""
    with patch("app.main.check_database_connection", new_callable=AsyncMock) as mock_db_check:
        mock_db_check.return_value = False

        response = client.get("/health")
        data = response.json()

        assert response.status_code == 503
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"]["status"] == "unhealthy"


def test_root_endpoint_returns_200(client: TestClient) -> None:
    """Test that root endpoint returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_returns_service_info(client: TestClient) -> None:
    """Test that root endpoint returns service metadata."""
    response = client.get("/")
    data = response.json()

    assert "service" in data
    assert "version" in data
    assert "status" in data
    assert data["service"] == "inference-gateway"
    assert data["status"] == "operational"
