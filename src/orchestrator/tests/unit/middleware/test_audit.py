import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_unit_tests_only_1234567890")

import pytest
from app.middleware.audit import audit_middleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    app = FastAPI()
    app.middleware("http")(audit_middleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.asyncio
async def test_audit_no_auth_header(client):
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    async_session_local = MagicMock(return_value=context_manager)
    with (
        patch("app.middleware.audit.AsyncSessionLocal", async_session_local),
        patch("app.middleware.audit.logger") as mock_logger,
    ):
        response = client.get("/test")
        assert response.status_code == 200
        session.add.assert_called_once()
        session.commit.assert_called_once()
        log_args = mock_logger.info.call_args_list[-1][1]["extra"]
        assert log_args["method"] == "GET"
        assert log_args["path"] == "/test"
        assert log_args["status_code"] == 200
        assert "user" not in log_args
        assert "duration_ms" in log_args
        assert "request_id" in log_args


@pytest.mark.asyncio
async def test_audit_invalid_auth_header(client):
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    async_session_local = MagicMock(return_value=context_manager)
    with (
        patch("app.middleware.audit.AsyncSessionLocal", async_session_local),
        patch("app.middleware.audit.logger") as mock_logger,
    ):
        response = client.get("/test", headers={"Authorization": "NotBearer token"})
        assert response.status_code == 200
        log_args = mock_logger.info.call_args_list[-1][1]["extra"]
        assert "user" not in log_args


@pytest.mark.asyncio
async def test_audit_valid_bearer_token(client):
    payload = {
        "sub": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "roles": ["admin", "developer"],
        "jti": "tokenid",
    }
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    async_session_local = MagicMock(return_value=context_manager)
    with (
        patch("app.middleware.audit.AsyncSessionLocal", async_session_local),
        patch("app.middleware.audit.jwt_validator.verify_token", return_value=payload),
        patch("app.middleware.audit.logger") as mock_logger,
    ):
        response = client.get("/test", headers={"Authorization": "Bearer validtoken"})
        assert response.status_code == 200
        log_args = mock_logger.info.call_args_list[-1][1]["extra"]
        assert log_args["user"] == payload["sub"]
        assert log_args["user_roles"] == payload["roles"]
        assert log_args["token_id"] == payload["jti"]
        session.add.assert_called_once()
        audit_record = session.add.call_args[0][0]
        assert audit_record.actor_roles == payload["roles"]
        assert audit_record.actor_user_id is not None


@pytest.mark.asyncio
async def test_audit_bearer_token_invalid_payload(client):
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    async_session_local = MagicMock(return_value=context_manager)
    with (
        patch("app.middleware.audit.AsyncSessionLocal", async_session_local),
        patch("app.middleware.audit.jwt_validator.verify_token", return_value=None),
        patch("app.middleware.audit.logger") as mock_logger,
    ):
        response = client.get("/test", headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 200
        log_args = mock_logger.info.call_args_list[-1][1]["extra"]
        assert "user" not in log_args


@pytest.mark.asyncio
async def test_audit_uses_request_header_request_id(client):
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    request_id = str(uuid.uuid4())
    async_session_local = MagicMock(return_value=context_manager)
    with (
        patch("app.middleware.audit.AsyncSessionLocal", async_session_local),
        patch("app.middleware.audit.logger") as mock_logger,
    ):
        response = client.get("/test", headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        log_args = mock_logger.info.call_args_list[-1][1]["extra"]
        assert log_args["request_id"] == request_id
        session.add.assert_called_once()
        audit_record = session.add.call_args[0][0]
        assert audit_record.request_id == request_id
