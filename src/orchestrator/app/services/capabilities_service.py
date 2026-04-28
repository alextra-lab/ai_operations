"""
Capabilities Service for Stateless Core v1

This module implements the capabilities service for feature flag management
and edition-based capability control (ADR-032).

Supports core/plus edition feature flags and capability queries.
"""

from typing import Any

from ..schemas.capabilities import (
    Capability,
    CapabilityCategory,
    CapabilityStatus,
    EditionCapabilities,
    FeatureFlags,
)


class CapabilitiesService:
    """Service for managing system capabilities and feature flags."""

    def __init__(self) -> None:
        """Initialize the capabilities service."""
        self._capabilities: dict[str, Capability] = {}
        self._feature_flags: FeatureFlags = FeatureFlags(
            expert_chunking=False,
            advanced_analytics=False,
            run_manifests=True,
            exports=True,
            summaries=True,
            preflight_analysis=True,
            quality_metrics=True,
            test_harness=True,
        )
        self._initialize_capabilities()

    def _initialize_capabilities(self) -> None:
        """Initialize the core capabilities for Stateless Core v1."""
        # Core capabilities (always available)
        self._capabilities["chunking_fixed_token"] = Capability(
            name="chunking_fixed_token",
            display_name="Fixed Token Chunking",
            description="Chunk documents using fixed token size strategy",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0.0",
        )

        self._capabilities["chunking_sliding_token"] = Capability(
            name="chunking_sliding_token",
            display_name="Sliding Token Chunking",
            description="Chunk documents using sliding window with overlap",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0.0",
        )

        self._capabilities["chunking_heading_aware"] = Capability(
            name="chunking_heading_aware",
            display_name="Heading-Aware Chunking",
            description="Chunk documents respecting heading boundaries",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0.0",
        )

        self._capabilities["run_manifests"] = Capability(
            name="run_manifests",
            display_name="Run Manifests",
            description="Store PII-free telemetry data for stateless architecture",
            category=CapabilityCategory.TELEMETRY,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0.0",
        )

        self._capabilities["telemetry_capture"] = Capability(
            name="telemetry_capture",
            display_name="Telemetry Capture",
            description="Capture execution metrics without conversation content",
            category=CapabilityCategory.TELEMETRY,
            status=CapabilityStatus.AVAILABLE,
            edition="core",
            version="1.0.0",
        )

        # Plus capabilities (feature-flagged)
        self._capabilities["chunking_semantic_adaptive"] = Capability(
            name="chunking_semantic_adaptive",
            display_name="Semantic Adaptive Chunking",
            description="Chunk documents using semantic similarity analysis",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.FEATURE_FLAGGED,
            edition="plus",
            version="1.0.0",
        )

        self._capabilities["chunking_page_block"] = Capability(
            name="chunking_page_block",
            display_name="Page Block Chunking",
            description="Chunk documents by page boundaries",
            category=CapabilityCategory.CHUNKING,
            status=CapabilityStatus.FEATURE_FLAGGED,
            edition="plus",
            version="1.0.0",
        )

        self._capabilities["preflight_analysis"] = Capability(
            name="preflight_analysis",
            display_name="Preflight Analysis",
            description="Analyze documents and recommend chunking strategies",
            category=CapabilityCategory.ANALYSIS,
            status=CapabilityStatus.FEATURE_FLAGGED,
            edition="plus",
            version="1.0.0",
        )

        self._capabilities["quality_metrics"] = Capability(
            name="quality_metrics",
            display_name="Quality Metrics",
            description="Calculate chunking quality scores and recommendations",
            category=CapabilityCategory.ANALYSIS,
            status=CapabilityStatus.FEATURE_FLAGGED,
            edition="plus",
            version="1.0.0",
        )

        # Future capabilities (disabled for v1)
        self._capabilities["history_provider"] = Capability(
            name="history_provider",
            display_name="History Provider",
            description="Store and retrieve conversation history",
            category=CapabilityCategory.STORAGE,
            status=CapabilityStatus.DISABLED,
            edition="plus",
            version="2.0.0",
        )

        self._capabilities["evidence_sink"] = Capability(
            name="evidence_sink",
            display_name="Evidence Sink",
            description="Store execution evidence and artifacts",
            category=CapabilityCategory.STORAGE,
            status=CapabilityStatus.DISABLED,
            edition="plus",
            version="2.0.0",
        )

        self._capabilities["crypto_provider"] = Capability(
            name="crypto_provider",
            display_name="Crypto Provider",
            description="Encrypt and decrypt sensitive data",
            category=CapabilityCategory.SECURITY,
            status=CapabilityStatus.DISABLED,
            edition="plus",
            version="2.0.0",
        )

    def get_capabilities(
        self,
        edition: str | None = None,
        category: CapabilityCategory | None = None,
        status: CapabilityStatus | None = None,
    ) -> list[Capability]:
        """
        Get capabilities with optional filtering.

        Args:
            edition: Filter by edition (core, plus)
            category: Filter by category
            status: Filter by status

        Returns:
            List of matching capabilities
        """
        capabilities = list(self._capabilities.values())

        if edition:
            capabilities = [c for c in capabilities if c.edition == edition]

        if category:
            capabilities = [c for c in capabilities if c.category == category]

        if status:
            capabilities = [c for c in capabilities if c.status == status]

        return capabilities

    def get_capability(self, name: str) -> Capability | None:
        """
        Get a specific capability by name.

        Args:
            name: Capability name

        Returns:
            Capability if found, None otherwise
        """
        return self._capabilities.get(name)

    def is_capability_available(self, name: str) -> bool:
        """
        Check if a capability is available.

        Args:
            name: Capability name

        Returns:
            True if capability is available, False otherwise
        """
        capability = self._capabilities.get(name)
        if not capability:
            return False

        # Check if capability is available based on status and feature flags
        if capability.status == CapabilityStatus.AVAILABLE:
            return True

        if capability.status == CapabilityStatus.FEATURE_FLAGGED:
            # Check feature flags for this capability
            if (
                capability.name == "chunking_semantic_adaptive"
                or capability.name == "chunking_page_block"
            ):
                return self._feature_flags.expert_chunking
            if capability.name == "preflight_analysis":
                return self._feature_flags.preflight_analysis
            if capability.name == "quality_metrics":
                return self._feature_flags.quality_metrics

        return False

    def get_edition_capabilities(self, edition: str) -> EditionCapabilities:
        """
        Get capabilities for a specific edition.

        Args:
            edition: Edition name (core, plus)

        Returns:
            Edition capabilities
        """
        capabilities = self.get_capabilities(edition=edition)
        available = [c for c in capabilities if self.is_capability_available(c.name)]
        disabled = [c for c in capabilities if not self.is_capability_available(c.name)]

        return EditionCapabilities(
            edition=edition,
            total_capabilities=len(capabilities),
            available_capabilities=len(available),
            capabilities=capabilities,
            available=available,
            disabled=disabled,
        )

    def get_feature_flags(self) -> FeatureFlags:
        """
        Get current feature flags.

        Returns:
            Current feature flags
        """
        return self._feature_flags

    def update_feature_flags(self, flags: FeatureFlags) -> None:
        """
        Update feature flags.

        Args:
            flags: New feature flags
        """
        self._feature_flags = flags

    def get_capability_categories(self) -> list[CapabilityCategory]:
        """
        Get all capability categories.

        Returns:
            List of capability categories
        """
        return list(CapabilityCategory)

    def get_capability_statuses(self) -> list[CapabilityStatus]:
        """
        Get all capability statuses.

        Returns:
            List of capability statuses
        """
        return list(CapabilityStatus)

    def get_system_info(self) -> dict[str, Any]:
        """
        Get system capability information.

        Returns:
            System information dictionary
        """
        total_capabilities = len(self._capabilities)
        available_capabilities = len(
            [c for c in self._capabilities.values() if self.is_capability_available(c.name)]
        )

        return {
            "total_capabilities": total_capabilities,
            "available_capabilities": available_capabilities,
            "feature_flags": self._feature_flags.model_dump(),
            "editions": ["core", "plus"],
            "categories": [cat.value for cat in CapabilityCategory],
            "statuses": [status.value for status in CapabilityStatus],
        }
