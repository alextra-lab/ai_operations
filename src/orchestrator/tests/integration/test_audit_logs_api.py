"""
Integration tests for audit log API endpoints.

These tests verify the full request/response cycle for audit log endpoints.
"""

import uuid
from datetime import UTC, datetime

import pytest
from app.main import create_app  # type: ignore[attr-defined]
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get admin access token."""
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Get regular user access token."""
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestAuditLogsAPI:
    """Test audit logs API endpoints."""

    def test_list_logs_requires_auth(self, client):
        """Test that authentication is required."""
        response = client.get("/admin/audit-logs")
        assert response.status_code == 401

    def test_list_logs_requires_admin_or_dev(self, client, user_token):
        """Test that regular users are denied access."""
        response = client.get(
            "/admin/audit-logs", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    def test_list_logs_success(self, client, admin_token):
        """Test successful audit log listing."""
        response = client.get(
            "/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["logs"], list)

    def test_list_logs_with_pagination(self, client, admin_token):
        """Test pagination parameters."""
        response = client.get(
            "/admin/audit-logs?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_logs_with_filters(self, client, admin_token):
        """Test filtering parameters."""
        response = client.get(
            "/admin/audit-logs?resource_type=http_request&success=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["logs"], list)

    def test_list_logs_with_search(self, client, admin_token):
        """Test search parameter."""
        response = client.get(
            "/admin/audit-logs?search=POST",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    def test_list_logs_with_date_range(self, client, admin_token):
        """Test date range filtering."""
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0).isoformat()
        end = datetime.now(UTC).isoformat()

        response = client.get(
            f"/admin/audit-logs?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    def test_get_stats_success(self, client, admin_token):
        """Test successful statistics retrieval."""
        response = client.get(
            "/admin/audit-logs/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_events" in data
        assert "success_count" in data
        assert "failure_count" in data
        assert "unique_users" in data
        assert "unique_resource_types" in data
        assert "top_actions" in data
        assert "top_resource_types" in data
        assert isinstance(data["top_actions"], list)
        assert isinstance(data["top_resource_types"], list)

    def test_get_stats_requires_auth(self, client):
        """Test that stats endpoint requires authentication."""
        response = client.get("/admin/audit-logs/stats")
        assert response.status_code == 401

    def test_get_log_by_id_not_found(self, client, admin_token):
        """Test 404 for non-existent log ID."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/admin/audit-logs/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_invalid_page_number(self, client, admin_token):
        """Test validation of page number."""
        response = client.get(
            "/admin/audit-logs?page=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422  # Validation error

    def test_invalid_page_size(self, client, admin_token):
        """Test validation of page size."""
        response = client.get(
            "/admin/audit-logs?page_size=1000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422  # Validation error

    def test_stats_with_filters(self, client, admin_token):
        """Test statistics with filters."""
        response = client.get(
            "/admin/audit-logs/stats?resource_type=http_request",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_events" in data
