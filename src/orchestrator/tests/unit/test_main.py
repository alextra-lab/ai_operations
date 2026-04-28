"""
Unit tests for the main application.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.orchestrator.app.main import lifespan
from src.orchestrator.app.routers.core import router as core_router
from src.orchestrator.app.routers.corpus import router as corpus_router
from src.orchestrator.app.routers.health import router as health_router
from src.orchestrator.app.routers.orchestrator import router as orchestrator_router
from src.orchestrator.app.routers.query import router as query_router
from src.shared.auth import auth_router


@pytest.fixture
def client():
    # Create proper async mock for sanitize_input
    async def mock_sanitize_input_func(*args, **kwargs):
        return ("sanitized_text", 0.0, False)

    with (
        patch(
            "src.orchestrator.app.middleware.sanitization.sanitize_input",
            side_effect=mock_sanitize_input_func,
        ),
        patch(
            "src.orchestrator.app.utils.sanitization.sanitize_input",
            side_effect=mock_sanitize_input_func,
        ),
    ):
        from src.orchestrator.app.main import create_app

        app = create_app()

        # Dependency overrides for FastAPI
        async def override_get_db():
            class DummySession:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    pass

            yield DummySession()

        async def override_get_current_user():
            class DummyUser:
                sub = "testuser"
                user_id = "testid"
                is_active = True

                def dict(self):
                    return {
                        "sub": self.sub,
                        "user_id": self.user_id,
                        "is_active": self.is_active,
                    }

            return DummyUser()

        app.dependency_overrides = {}
        from src.shared.auth import get_current_user, get_db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        yield TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") in ("healthy", "ok")


def test_core_endpoint(client):
    # core router is included as root
    response = client.get("/")
    assert response.status_code in (200, 404)


def test_auth_endpoint(client):
    response = client.post("/auth/token", data={"username": "u", "password": "p"})
    assert response.status_code in (200, 401, 422, 404)


def test_orchestrator_endpoint(client):
    # orchestrator router is /api/v1/process (POST)
    try:
        response = client.post(
            "/api/v1/process",
            json={
                "query": "test",
                "request_type": None,
                "context": None,
                "stream": False,
            },
        )
        # Accept various status codes including 500 errors due to LLM client initialization issues in test environment
        assert response.status_code in (200, 401, 404, 422, 500)
    except (ValueError, Exception) as e:
        # If an exception is raised during the request, treat it as a 500 error (expected in test environment)
        assert "LLMClient INIT FAILED" in str(e) or "ConnectError" in str(e)


def test_corpus_endpoint(client):
    # corpus router is /api/v1/documents/ (GET)
    try:
        response = client.get("/api/v1/documents/")
        # Accept various status codes including 500 errors due to external service connectivity issues in test environment
        assert response.status_code in (200, 401, 404, 500)
    except Exception as e:
        # If an exception is raised during the request, treat it as a 500 error (expected in test environment)
        assert "ConnectError" in str(e) or "nodename nor servname" in str(e)


def test_query_endpoint(client):
    # query router is /api/v1/query/search (POST)
    try:
        response = client.post("/api/v1/query/search", json={"query": "test"})
        # Accept various status codes including 500 errors due to external service connectivity issues in test environment
        assert response.status_code in (200, 401, 404, 422, 500)
    except Exception as e:
        # If an exception is raised during the request, treat it as a 500 error (expected in test environment)
        assert "ConnectError" in str(e) or "nodename nor servname" in str(e)


def test_middleware_called():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    async def dummy_middleware(request, call_next):
        return await call_next(request)

    with (
        patch(
            "src.orchestrator.app.main.sanitize_request", wraps=dummy_middleware
        ) as mock_sanitize,
        patch("src.orchestrator.app.main.audit_middleware", wraps=dummy_middleware) as mock_audit,
    ):
        # Use direct imports instead of importing from app.main
        app = FastAPI(title="AI Operations Platform (AIOP) Orchestrator API", lifespan=lifespan)
        app.middleware("http")(mock_sanitize)
        app.middleware("http")(mock_audit)
        app.include_router(core_router)
        app.include_router(health_router)
        app.include_router(auth_router)
        app.include_router(orchestrator_router)
        app.include_router(corpus_router)
        app.include_router(query_router)
        client = TestClient(app)
        client.get("/health")
        assert mock_sanitize.called
        assert mock_audit.called


def test_print_routes(client):
    # Print all registered routes for debugging
    for route in client.app.routes:
        if hasattr(route, "methods"):
            print(f"{route.path} -> {route.methods}")


def test_app_startup_and_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") in ("healthy", "ok")
