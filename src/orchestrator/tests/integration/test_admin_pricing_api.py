"""
Integration tests for admin pricing endpoints (ADR-046).
"""

import pytest
from app.main import create_app  # type: ignore[attr-defined]
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_token(client: TestClient):
    resp = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _pick_any_model_id(client: TestClient, admin_token: str) -> str:
    resp = client.get(
        "/api/v1/models?page=1&size=1&available_only=false&include_hidden=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("models")
    return str(data["models"][0]["model_id"])


class TestAdminPricingAPI:
    def test_auth_required(self, client: TestClient):
        resp = client.get("/api/v1/admin/pricing/models/foo/pricing/current")
        assert resp.status_code in (401, 403)

    def test_set_and_get_pricing_flow(self, client: TestClient, admin_token: str):
        model_id = _pick_any_model_id(client, admin_token)

        # Set a new price
        body = {
            "input_price_per_million": 1.23456,
            "output_price_per_million": 2.34567,
            "change_reason": "integration test",
        }
        resp = client.post(
            f"/api/v1/admin/pricing/models/{model_id}/pricing/change",
            json=body,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        current = resp.json()
        assert current["model_id"] == model_id
        assert current["currency"] == "EUR"

        # Fetch current pricing
        resp2 = client.get(
            f"/api/v1/admin/pricing/models/{model_id}/pricing/current",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp2.status_code == 200
        cur2 = resp2.json()
        assert cur2["model_id"] == model_id
        assert cur2["currency"] == "EUR"

        # Fetch history and ensure at least one entry
        resp3 = client.get(
            f"/api/v1/admin/pricing/models/{model_id}/pricing/history",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp3.status_code == 200
        history = resp3.json()
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_pricing_endpoints_with_encoded_slash_in_model_id(
        self, client: TestClient, admin_token: str
    ):
        """Test that pricing endpoints handle URL-encoded slashes in model IDs."""
        # Model ID with slash: "openai/gpt-oss-120b" -> URL-encoded as "openai%2Fgpt-oss-120b"
        encoded_model_id = "openai%2Fgpt-oss-120b"

        # Test current pricing endpoint - should return 404 (no pricing) not route 404
        resp = client.get(
            f"/api/v1/admin/pricing/models/{encoded_model_id}/pricing/current",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Should get 404 with "No pricing configured" message, not route 404
        assert resp.status_code == 404
        assert "No pricing configured" in resp.json()["detail"]

        # Test history endpoint - should return empty list, not route 404
        resp2 = client.get(
            f"/api/v1/admin/pricing/models/{encoded_model_id}/pricing/history",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), list)
