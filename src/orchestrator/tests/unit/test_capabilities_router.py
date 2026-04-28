"""
Unit tests for capabilities router.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.orchestrator.app.routers.capabilities import router
from src.orchestrator.app.schemas.capabilities import (
    Capability,
    CapabilityCategory,
    CapabilityStatus,
    EditionCapabilities,
    FeatureFlags,
)


class TestCapabilitiesRouter:
    """Test cases for capabilities router."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(router)

    @pytest.fixture
    def mock_capabilities_service(self):
        """Create mock capabilities service."""
        with patch("src.orchestrator.app.routers.capabilities._capabilities_service") as mock:
            yield mock

    def test_get_capabilities_all(self, client, mock_capabilities_service):
        """Test getting all capabilities."""
        mock_capabilities = [
            Capability(
                name="chunking_fixed_token",
                display_name="Fixed Token Chunking",
                description="Basic fixed-size token chunking",
                category=CapabilityCategory.CHUNKING,
                status=CapabilityStatus.AVAILABLE,
                edition="core",
                version="1.0",
            )
        ]
        mock_capabilities_service.get_capabilities.return_value = mock_capabilities

        response = client.get("/api/v1/capabilities/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "chunking_fixed_token"

    def test_get_capabilities_filtered(self, client, mock_capabilities_service):
        """Test getting filtered capabilities."""
        mock_capabilities = []
        mock_capabilities_service.get_capabilities.return_value = mock_capabilities

        response = client.get("/api/v1/capabilities/?edition=core&category=chunking")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_capability_by_name(self, client, mock_capabilities_service):
        """Test getting capability by name."""
        mock_capability = Capability(
            name="chunking_fixed_token",
            display_name="Fixed Token Chunking",
            description="Basic fixed-size token chunking",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0",
        )
        mock_capabilities_service.get_capability.return_value = mock_capability

        response = client.get("/api/v1/capabilities/chunking_fixed_token")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "chunking_fixed_token"

    def test_get_capability_by_name_not_found(self, client, mock_capabilities_service):
        """Test getting non-existent capability."""
        mock_capabilities_service.get_capability.return_value = None

        # The router will raise HTTPException, which FastAPI converts to 404
        response = client.get("/api/v1/capabilities/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "Capability not found" in data["detail"]

    def test_get_edition_capabilities(self, client, mock_capabilities_service):
        """Test getting edition capabilities."""
        mock_edition_capabilities = EditionCapabilities(
            edition="core",
            total_capabilities=5,
            available_capabilities=4,
            capabilities=[],
            available=[],
            disabled=[],
        )
        mock_capabilities_service.get_edition_capabilities.return_value = mock_edition_capabilities

        response = client.get("/api/v1/capabilities/editions/core")
        assert response.status_code == 200
        data = response.json()
        assert data["edition"] == "core"
        assert data["total_capabilities"] == 5

    def test_get_feature_flags(self, client, mock_capabilities_service):
        """Test getting feature flags."""
        mock_feature_flags = FeatureFlags(
            expert_chunking=False,
            preflight_analysis=True,
            quality_metrics=True,
            advanced_analytics=False,
        )
        mock_capabilities_service.get_feature_flags.return_value = mock_feature_flags

        response = client.get("/api/v1/capabilities/feature-flags")
        assert response.status_code == 200
        data = response.json()
        assert data["expert_chunking"] is False
        assert data["preflight_analysis"] is True

    def test_update_feature_flags(self, client, mock_capabilities_service):
        """Test updating feature flags."""
        mock_feature_flags = FeatureFlags(
            expert_chunking=True,
            preflight_analysis=False,
            quality_metrics=True,
            advanced_analytics=True,
        )
        mock_capabilities_service.update_feature_flags.return_value = mock_feature_flags

        response = client.put(
            "/api/v1/capabilities/feature-flags",
            json={
                "expert_chunking": True,
                "preflight_analysis": False,
                "quality_metrics": True,
                "advanced_analytics": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["expert_chunking"] is True

    def test_get_system_info(self, client, mock_capabilities_service):
        """Test getting system information."""
        mock_system_info = {
            "edition": "core",
            "provider_types": {"history": "none", "evidence": "none", "crypto": "none"},
            "feature_flags": {"expert_chunking": False},
            "total_capabilities": 5,
            "available_capabilities": 4,
        }
        mock_capabilities_service.get_system_info.return_value = mock_system_info

        response = client.get("/api/v1/capabilities/system/info")
        assert response.status_code == 200
        data = response.json()
        assert data["edition"] == "core"
        assert data["total_capabilities"] == 5
