from unittest.mock import patch

import pytest
from app.routers.core import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/core")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_read_root(client):
    with patch("app.routers.core.logger") as mock_logger:
        response = client.get("/core/")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello from Orchestrator API"
        assert mock_logger.info.called


from pydantic import BaseModel


def test_protected_route(client, app):
    class FakeUser(BaseModel):
        sub: str
        user_id: int

    fake_user = FakeUser(sub="alice", user_id=123)
    from app.routers import core

    app.dependency_overrides[core.get_current_user] = lambda: fake_user
    with patch("app.routers.core.logger") as mock_logger:
        response = client.get("/core/protected")
        assert response.status_code == 200
        data = response.json()
        assert data["message"].startswith("You have access")
        assert data["user"]["sub"] == "alice"
        assert data["user"]["user_id"] == 123
        assert mock_logger.info.called
    app.dependency_overrides = {}
