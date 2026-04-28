"""
Integration tests for RBAC V2 admin endpoints.
"""

import os
import sys
import uuid
from pathlib import Path

# Load test environment variables before importing app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ops" / "testing"))
from load_test_env import load_test_env  # type: ignore[import-not-found]

load_test_env()

# Override with integration test specific values only if not already set
# This allows env.test to provide values, but provides defaults for CI/local testing
if "POSTGRES_HOST" not in os.environ:
    os.environ["POSTGRES_HOST"] = "localhost"
if "POSTGRES_PORT" not in os.environ:
    os.environ["POSTGRES_PORT"] = "5433"
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "aio-test"
if "POSTGRES_USER" not in os.environ:
    os.environ["POSTGRES_USER"] = os.environ.get("TEST_DB_USER", "testuser")
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = os.environ.get("TEST_DB_PASSWORD", "test_password_123")

# Construct DATABASE_URL from components if not explicitly set
if "DATABASE_URL" not in os.environ:
    db_user = os.environ["POSTGRES_USER"]
    db_password = os.environ["POSTGRES_PASSWORD"]
    db_host = os.environ["POSTGRES_HOST"]
    db_port = os.environ["POSTGRES_PORT"]
    db_name = os.environ["POSTGRES_DB"]
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

import pytest
from app.main import create_app  # type: ignore[attr-defined]
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_token(client: TestClient):
    """Get admin authentication token from environment variables."""
    admin_username = os.environ.get("TEST_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("TEST_ADMIN_PASSWORD", "adminpassword")
    resp = client.post(
        "/auth/token",
        data={"username": admin_username, "password": admin_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestGroupingRoles:
    def test_create_and_list_grouping_role(self, client: TestClient, admin_token: str):
        role_name = f"threat_hunting_{uuid.uuid4().hex[:6]}"

        create_resp = client.post(
            "/api/v1/admin/grouping-roles",
            json={"role_name": role_name},
            headers=_auth_headers(admin_token),
        )
        assert create_resp.status_code == 201

        list_resp = client.get(
            "/api/v1/admin/grouping-roles",
            headers=_auth_headers(admin_token),
        )
        assert list_resp.status_code == 200
        roles = [item["role_name"] for item in list_resp.json()]
        assert role_name in roles


class TestDeveloperTeams:
    def test_create_team_and_list(self, client: TestClient, admin_token: str):
        team_id = f"team:csirt_{uuid.uuid4().hex[:6]}"

        create_resp = client.post(
            "/api/v1/admin/developer-teams",
            json={"team_id": team_id},
            headers=_auth_headers(admin_token),
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["team_id"] == team_id

        list_resp = client.get(
            "/api/v1/admin/developer-teams",
            headers=_auth_headers(admin_token),
        )
        assert list_resp.status_code == 200
        teams = [item["team_id"] for item in list_resp.json()]
        assert team_id in teams


class TestRoleCollections:
    def test_list_role_collections_empty(self, client: TestClient, admin_token: str):
        resp = client.get(
            "/admin/roles/test-role/collections",
            headers=_auth_headers(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_name"] == "test-role"
        assert data["total"] == 0
