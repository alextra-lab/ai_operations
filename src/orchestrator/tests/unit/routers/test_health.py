from unittest.mock import patch

import pytest
from app.routers.health import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_health_check(client):
    with patch("app.routers.health.logger") as mock_logger:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert mock_logger.info.called
