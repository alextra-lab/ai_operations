from unittest.mock import AsyncMock, patch

import pytest
from app.middleware.sanitization import sanitize_request
from app.middleware.security_headers import security_headers_middleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    app = FastAPI()
    app.middleware("http")(sanitize_request)
    app.middleware("http")(security_headers_middleware)

    @app.post("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/test")
    async def test_get():
        return {"ok": True}

    @app.patch("/test")
    async def test_patch():
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_post_valid_utf8_body(client):
    with (
        patch(
            "app.middleware.sanitization.sanitize_input",
            new=AsyncMock(return_value=("clean", 0.1, False)),
        ) as mock_sanitize,
        patch("app.middleware.sanitization.logger") as mock_logger,
    ):
        response = client.post("/test", data="hello", headers={"content-type": "application/json"})
        assert response.status_code == 200
        assert mock_sanitize.await_count == 1
        assert mock_logger.info.called


def test_post_non_utf8_body(client):
    # Simulate a body that is not valid UTF-8 but is valid latin-1
    bad_bytes = b"caf\xe9"  # 'café' in latin-1
    with (
        patch(
            "app.middleware.sanitization.sanitize_input",
            new=AsyncMock(return_value=("clean", 0.1, False)),
        ) as mock_sanitize,
        patch("app.middleware.sanitization.logger") as mock_logger,
    ):
        response = client.post(
            "/test", data=bad_bytes, headers={"content-type": "application/json"}
        )
        assert response.status_code == 200
        assert mock_sanitize.await_count == 1
        assert any("latin-1" in str(call) for call in mock_logger.warning.call_args_list)


def test_post_empty_body(client):
    with patch("app.middleware.sanitization.logger") as mock_logger:
        response = client.post("/test", data="", headers={"content-type": "application/json"})
        assert response.status_code == 200
        assert any("empty" in str(call) for call in mock_logger.info.call_args_list)


def test_post_multipart_skips_sanitization(client):
    with patch("app.middleware.sanitization.logger") as mock_logger:
        response = client.post(
            "/test",
            data="irrelevant",
            headers={"content-type": "multipart/form-data; boundary=abc"},
        )
        assert response.status_code == 200
        assert any("Skipping sanitization" in str(call) for call in mock_logger.info.call_args_list)


def test_get_no_body_sanitization(client):
    with patch("app.middleware.sanitization.logger") as mock_logger:
        response = client.get("/test")
        assert response.status_code == 200
        assert any("No body sanitization" in str(call) for call in mock_logger.debug.call_args_list)


def test_patch_valid_body(client):
    with (
        patch(
            "app.middleware.sanitization.sanitize_input",
            new=AsyncMock(return_value=("clean", 0.1, False)),
        ) as mock_sanitize,
        patch("app.middleware.sanitization.logger") as mock_logger,
    ):
        response = client.patch(
            "/test", data="patchdata", headers={"content-type": "application/json"}
        )
        assert response.status_code == 200
        assert mock_sanitize.await_count == 1
        assert mock_logger.info.called
