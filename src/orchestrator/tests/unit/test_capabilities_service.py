"""
Unit tests for CapabilitiesService

Tests the capabilities service functionality for Stateless Core v1.
"""

import pytest

from src.orchestrator.app.schemas.capabilities import (
    CapabilityCategory,
    CapabilityStatus,
    FeatureFlags,
)
from src.orchestrator.app.services.capabilities_service import CapabilitiesService


class TestCapabilitiesService:
    """Test cases for CapabilitiesService."""

    @pytest.fixture
    def capabilities_service(self):
        """Create a capabilities service instance for testing."""
        return CapabilitiesService()

    def test_initialization(self, capabilities_service):
        """Test service initialization."""
        assert capabilities_service is not None
        assert hasattr(capabilities_service, "_capabilities")
        assert hasattr(capabilities_service, "_feature_flags")

    def test_get_capabilities_all(self, capabilities_service):
        """Test getting all capabilities."""
        capabilities = capabilities_service.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

        # Check that all capabilities have required fields
        for capability in capabilities:
            assert hasattr(capability, "name")
            assert hasattr(capability, "display_name")
            assert hasattr(capability, "description")
            assert hasattr(capability, "category")
            assert hasattr(capability, "status")
            assert hasattr(capability, "edition")
            assert hasattr(capability, "version")

    def test_get_capabilities_filtered_by_edition(self, capabilities_service):
        """Test getting capabilities filtered by edition."""
        core_capabilities = capabilities_service.get_capabilities(edition="core")
        plus_capabilities = capabilities_service.get_capabilities(edition="plus")

        assert isinstance(core_capabilities, list)
        assert isinstance(plus_capabilities, list)

        # All core capabilities should have edition="core"
        for capability in core_capabilities:
            assert capability.edition == "core"

        # All plus capabilities should have edition="plus"
        for capability in plus_capabilities:
            assert capability.edition == "plus"

    def test_get_capabilities_filtered_by_category(self, capabilities_service):
        """Test getting capabilities filtered by category."""
        chunking_capabilities = capabilities_service.get_capabilities(
            category=CapabilityCategory.CHUNKING
        )
        telemetry_capabilities = capabilities_service.get_capabilities(
            category=CapabilityCategory.TELEMETRY
        )

        assert isinstance(chunking_capabilities, list)
        assert isinstance(telemetry_capabilities, list)

        # All chunking capabilities should have category=CHUNKING
        for capability in chunking_capabilities:
            assert capability.category == CapabilityCategory.CHUNKING

        # All telemetry capabilities should have category=TELEMETRY
        for capability in telemetry_capabilities:
            assert capability.category == CapabilityCategory.TELEMETRY

    def test_get_capabilities_filtered_by_status(self, capabilities_service):
        """Test getting capabilities filtered by status."""
        available_capabilities = capabilities_service.get_capabilities(
            status=CapabilityStatus.AVAILABLE
        )
        disabled_capabilities = capabilities_service.get_capabilities(
            status=CapabilityStatus.DISABLED
        )

        assert isinstance(available_capabilities, list)
        assert isinstance(disabled_capabilities, list)

        # All available capabilities should have status=AVAILABLE
        for capability in available_capabilities:
            assert capability.status == CapabilityStatus.AVAILABLE

        # All disabled capabilities should have status=DISABLED
        for capability in disabled_capabilities:
            assert capability.status == CapabilityStatus.DISABLED

    def test_get_capability_by_name(self, capabilities_service):
        """Test getting a specific capability by name."""
        # Test existing capability
        capability = capabilities_service.get_capability("chunking_fixed_token")
        assert capability is not None
        assert capability.name == "chunking_fixed_token"
        assert capability.display_name == "Fixed Token Chunking"

        # Test non-existent capability
        capability = capabilities_service.get_capability("non_existent_capability")
        assert capability is None

    def test_is_capability_available(self, capabilities_service):
        """Test checking capability availability."""
        # Test available capability
        assert capabilities_service.is_capability_available("chunking_fixed_token") is True
        assert capabilities_service.is_capability_available("run_manifests") is True

        # Test feature-flagged capability (should depend on feature flags)
        # This will depend on the current feature flag settings
        semantic_available = capabilities_service.is_capability_available(
            "chunking_semantic_adaptive"
        )
        assert isinstance(semantic_available, bool)

        # Test disabled capability
        assert capabilities_service.is_capability_available("history_provider") is False

        # Test non-existent capability
        assert capabilities_service.is_capability_available("non_existent") is False

    def test_get_edition_capabilities(self, capabilities_service):
        """Test getting capabilities for a specific edition."""
        core_capabilities = capabilities_service.get_edition_capabilities("core")
        plus_capabilities = capabilities_service.get_edition_capabilities("plus")

        assert core_capabilities.edition == "core"
        assert plus_capabilities.edition == "plus"
        assert core_capabilities.total_capabilities > 0
        assert plus_capabilities.total_capabilities > 0

        # Check that available + disabled = total
        assert (
            core_capabilities.available_capabilities + len(core_capabilities.disabled)
            == core_capabilities.total_capabilities
        )

    def test_get_feature_flags(self, capabilities_service):
        """Test getting feature flags."""
        flags = capabilities_service.get_feature_flags()
        assert isinstance(flags, FeatureFlags)
        assert hasattr(flags, "expert_chunking")
        assert hasattr(flags, "advanced_analytics")
        assert hasattr(flags, "run_manifests")
        assert hasattr(flags, "preflight_analysis")
        assert hasattr(flags, "quality_metrics")

    def test_update_feature_flags(self, capabilities_service):
        """Test updating feature flags."""
        capabilities_service.get_feature_flags()

        # Create new flags
        new_flags = FeatureFlags(
            expert_chunking=True,
            advanced_analytics=True,
            run_manifests=True,
            exports=True,
            summaries=True,
            preflight_analysis=True,
            quality_metrics=True,
            test_harness=True,
        )

        # Update flags
        capabilities_service.update_feature_flags(new_flags)
        updated_flags = capabilities_service.get_feature_flags()

        assert updated_flags.expert_chunking is True
        assert updated_flags.advanced_analytics is True
        assert updated_flags.run_manifests is True
        assert updated_flags.preflight_analysis is True
        assert updated_flags.quality_metrics is True

    def test_get_capability_categories(self, capabilities_service):
        """Test getting capability categories."""
        categories = capabilities_service.get_capability_categories()
        assert isinstance(categories, list)
        assert CapabilityCategory.CHUNKING in categories
        assert CapabilityCategory.TELEMETRY in categories
        assert CapabilityCategory.ANALYSIS in categories
        assert CapabilityCategory.STORAGE in categories
        assert CapabilityCategory.SECURITY in categories

    def test_get_capability_statuses(self, capabilities_service):
        """Test getting capability statuses."""
        statuses = capabilities_service.get_capability_statuses()
        assert isinstance(statuses, list)
        assert CapabilityStatus.AVAILABLE in statuses
        assert CapabilityStatus.FEATURE_FLAGGED in statuses
        assert CapabilityStatus.DISABLED in statuses

    def test_get_system_info(self, capabilities_service):
        """Test getting system information."""
        info = capabilities_service.get_system_info()
        assert isinstance(info, dict)
        assert "total_capabilities" in info
        assert "available_capabilities" in info
        assert "feature_flags" in info
        assert "editions" in info
        assert "categories" in info
        assert "statuses" in info

        assert info["total_capabilities"] > 0
        assert info["available_capabilities"] >= 0
        assert "core" in info["editions"]
        assert "plus" in info["editions"]

    def test_core_capabilities_always_available(self, capabilities_service):
        """Test that core capabilities are always available."""
        core_capabilities = capabilities_service.get_capabilities(edition="core")

        for capability in core_capabilities:
            if capability.status == CapabilityStatus.AVAILABLE:
                assert capabilities_service.is_capability_available(capability.name) is True

    def test_feature_flagged_capabilities(self, capabilities_service):
        """Test feature-flagged capabilities."""
        # Get feature-flagged capabilities
        flagged_capabilities = capabilities_service.get_capabilities(
            status=CapabilityStatus.FEATURE_FLAGGED
        )

        assert len(flagged_capabilities) > 0

        for capability in flagged_capabilities:
            assert capability.status == CapabilityStatus.FEATURE_FLAGGED
            # Availability should depend on feature flags
            is_available = capabilities_service.is_capability_available(capability.name)
            assert isinstance(is_available, bool)

    def test_disabled_capabilities(self, capabilities_service):
        """Test disabled capabilities."""
        # Get disabled capabilities
        disabled_capabilities = capabilities_service.get_capabilities(
            status=CapabilityStatus.DISABLED
        )

        for capability in disabled_capabilities:
            assert capability.status == CapabilityStatus.DISABLED
            assert capabilities_service.is_capability_available(capability.name) is False

    def test_capability_metadata(self, capabilities_service):
        """Test capability metadata completeness."""
        capabilities = capabilities_service.get_capabilities()

        for capability in capabilities:
            # Check required fields
            assert capability.name is not None
            assert capability.display_name is not None
            assert capability.description is not None
            assert capability.category is not None
            assert capability.status is not None
            assert capability.edition is not None
            assert capability.version is not None

            # Check field types
            assert isinstance(capability.name, str)
            assert isinstance(capability.display_name, str)
            assert isinstance(capability.description, str)
            assert isinstance(capability.category, CapabilityCategory)
            assert isinstance(capability.status, CapabilityStatus)
            assert isinstance(capability.edition, str)
            assert isinstance(capability.version, str)

            # Check edition values
            assert capability.edition in ["core", "plus"]

            # Check version format (should be semantic version)
            version_parts = capability.version.split(".")
            assert len(version_parts) == 3  # Major.Minor.Patch
            for part in version_parts:
                assert part.isdigit()
