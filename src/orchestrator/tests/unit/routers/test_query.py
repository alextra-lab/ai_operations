from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.routers.query import get_current_user, router
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


@pytest.fixture
def fake_user():
    return {"sub": "alice", "id": "user1"}


@pytest.fixture(autouse=True)
def override_get_current_user(app, fake_user):
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
def test_search_documents(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"results": [1, 2]}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/query/search", json={"query": "test"})
        assert response.status_code == 200
        assert response.json()["results"] == [1, 2]


@pytest.mark.asyncio
def test_ask_question(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"results": [1]}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/query/ask", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["sources"] == [1]
        assert data["confidence"] == 0.8


@pytest.mark.asyncio
def test_get_hot_documents(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=[{"id": 1}]))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/analytics/documents/hot")
        assert response.status_code == 200
        assert response.json()[0]["id"] == 1


@pytest.mark.asyncio
def test_get_usage_statistics(client):
    mock_instance = MagicMock()
    # Simulate a new structure returned by /analytics/performance-metrics
    fake_metrics = {"total_requests": 42, "active_users": 5}
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=fake_metrics))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/analytics/usage/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "active_users" in data


@pytest.mark.asyncio
def test_search_documents_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=400, text="fail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/query/search", json={"query": "test"})
        assert response.status_code == 400
        assert "fail" in response.text


@pytest.mark.asyncio
def test_ask_question_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=400, text="askfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/query/ask", json={"query": "test"})
        assert response.status_code == 400
        assert "askfail" in response.text


@pytest.mark.asyncio
def test_get_hot_documents_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="hotfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/analytics/documents/hot")
        assert response.status_code == 400
        assert "hotfail" in response.text


@pytest.mark.asyncio
def test_get_usage_statistics_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="usagefail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/analytics/usage/stats")
        assert response.status_code == 400
        assert "usagefail" in response.text


def test_get_forward_headers():
    from app.routers import query as query_mod

    class DummyRequest:
        headers = {"authorization": "Bearer test"}

    assert query_mod.get_forward_headers(DummyRequest()) == {"Authorization": "Bearer test"}

    class DummyRequest2:
        headers = {}

    assert query_mod.get_forward_headers(DummyRequest2()) == {}


def test_get_user_id():
    from app.routers import query as query_mod

    # dict with id
    assert query_mod.get_user_id({"id": 1}) == "1"
    # dict with sub
    assert query_mod.get_user_id({"sub": "bob"}) == "bob"

    # object with id
    class U:
        id = 2

    assert query_mod.get_user_id(U()) == "2"

    # object with sub
    class U2:
        sub = "carol"

    assert query_mod.get_user_id(U2()) == "carol"
    # neither
    assert query_mod.get_user_id({}) is None

    class U3:
        pass

    assert query_mod.get_user_id(U3()) is None
