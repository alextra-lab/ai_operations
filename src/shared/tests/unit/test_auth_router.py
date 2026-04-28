from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from shared.auth.models import TokenPayload
from shared.auth.router import create_auth_router, get_db


@pytest.fixture
def app():
    with patch(
        "shared.auth.router.auth_manager.get_current_user",
        return_value=lambda: TokenPayload(
            sub="admin",
            user_id="1",
            roles=["admin"],  # Multi-role support per ADR-060
            exp=1,
            iat=1,
            iss="iss",
            token_type="access",
        ),
    ):
        app = FastAPI()
        app.dependency_overrides[get_db] = lambda: (yield MagicMock())
        app.include_router(create_auth_router())
        yield app


def test_login_invalid_credentials(app):
    with patch("shared.auth.router.auth_manager.authenticate_user", return_value=None):
        client = TestClient(app)
        response = client.post("/auth/token", data={"username": "bad", "password": "bad"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.text


def test_refresh_invalid_format(app):
    with patch("shared.auth.router.auth_manager.verify_token", return_value=None):
        client = TestClient(app)
        response = client.post("/auth/refresh", json={"refresh_token": "bad"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token format" in response.text


def test_refresh_invalid_db(app):
    with (
        patch(
            "shared.auth.router.auth_manager.verify_token",
            return_value={"token_type": "refresh"},
        ),
        patch("shared.auth.router.auth_manager.validate_refresh_token", return_value=None),
    ):
        client = TestClient(app)
        response = client.post("/auth/refresh", json={"refresh_token": "bad"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "revoked" in response.text


def test_revoke_invalid_token(app):
    payload = TokenPayload(
        sub="admin",
        user_id="1",
        roles=["admin"],  # Multi-role support per ADR-060
        exp=1,
        iat=1,
        iss="iss",
        token_type="access",
    )
    app.dependency_overrides["shared.auth.router.auth_manager.get_current_user"] = (
        lambda: lambda: payload
    )
    with patch("shared.auth.router.auth_manager.revoke_refresh_token", return_value=False):
        client = TestClient(app)
        response = client.post("/auth/revoke", json={"refresh_token": "bad"})
        assert response.status_code == 400
        assert "already revoked" in response.text
