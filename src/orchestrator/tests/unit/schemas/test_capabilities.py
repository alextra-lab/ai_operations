"""Unit tests for capabilities schemas."""

import pytest
from app.schemas.capabilities import (
    CapabilitiesResponse,
    CapabilityDetails,
    CapabilityHealthCheck,
    CapabilityInfo,
    CapabilityMetrics,
    CapabilityRequest,
    CapabilityStatus,
    Edition,
    FeatureFlags,
    ProviderConfig,
    ProviderType,
    SystemInfo,
)


class TestEdition:
    """Test Edition enum."""

    def test_edition_values(self) -> None:
        """Test that Edition has correct values."""
        assert Edition.CORE == "core"
        assert Edition.PLUS == "plus"


class TestProviderType:
    """Test ProviderType enum."""

    def test_provider_type_values(self) -> None:
        """Test that ProviderType has correct values."""
        assert ProviderType.NONE == "none"
        assert ProviderType.GOVERNED == "governed"


class TestCapabilityStatus:
    """Test CapabilityStatus enum."""

    def test_capability_status_values(self) -> None:
        """Test that CapabilityStatus has correct values."""
        assert CapabilityStatus.AVAILABLE == "available"
        assert CapabilityStatus.DISABLED == "disabled"
        assert CapabilityStatus.EXPERIMENTAL == "experimental"
        assert CapabilityStatus.DEPRECATED == "deprecated"


class TestCapabilityInfo:
    """Test CapabilityInfo schema."""

    def test_valid_capability_info(self) -> None:
        """Test creating a valid capability info."""
        info = CapabilityInfo(
            name="conversation_storage",
            status=CapabilityStatus.AVAILABLE,
            description="Store conversation history",
            edition_required=Edition.PLUS,
            provider_required=ProviderType.GOVERNED,
            config={"max_size": "1GB", "retention": "30d"},
        )

        assert info.name == "conversation_storage"
        assert info.status == CapabilityStatus.AVAILABLE
        assert info.description == "Store conversation history"
        assert info.edition_required == Edition.PLUS
        assert info.provider_required == ProviderType.GOVERNED
        assert info.config == {"max_size": "1GB", "retention": "30d"}

    def test_optional_provider_required(self) -> None:
        """Test optional provider_required."""
        info = CapabilityInfo(
            name="basic_analytics",
            status=CapabilityStatus.AVAILABLE,
            description="Basic analytics",
            edition_required=Edition.CORE,
        )

        assert info.provider_required is None
        assert info.config == {}


class TestProviderConfig:
    """Test ProviderConfig schema."""

    def test_valid_provider_config(self) -> None:
        """Test creating a valid provider config."""
        config = ProviderConfig(
            history=ProviderType.GOVERNED,
            evidence=ProviderType.GOVERNED,
            crypto=ProviderType.GOVERNED,
        )

        assert config.history == ProviderType.GOVERNED
        assert config.evidence == ProviderType.GOVERNED
        assert config.crypto == ProviderType.GOVERNED

    def test_none_providers(self) -> None:
        """Test none providers."""
        config = ProviderConfig(
            history=ProviderType.NONE,
            evidence=ProviderType.NONE,
            crypto=ProviderType.NONE,
        )

        assert config.history == ProviderType.NONE
        assert config.evidence == ProviderType.NONE
        assert config.crypto == ProviderType.NONE


class TestFeatureFlags:
    """Test FeatureFlags schema."""

    def test_valid_feature_flags(self) -> None:
        """Test creating valid feature flags."""
        flags = FeatureFlags(
            expert_chunking=True,
            advanced_analytics=True,
            run_manifests=True,
            exports=True,
            summaries=True,
            preflight_analysis=True,
            quality_metrics=True,
            test_harness=True,
        )

        assert flags.expert_chunking is True
        assert flags.advanced_analytics is True
        assert flags.run_manifests is True
        assert flags.exports is True
        assert flags.summaries is True
        assert flags.preflight_analysis is True
        assert flags.quality_metrics is True
        assert flags.test_harness is True

    def test_default_values(self) -> None:
        """Test default values."""
        flags = FeatureFlags()

        assert flags.expert_chunking is False
        assert flags.advanced_analytics is False
        assert flags.run_manifests is True
        assert flags.exports is True
        assert flags.summaries is True
        assert flags.preflight_analysis is True
        assert flags.quality_metrics is True
        assert flags.test_harness is True


class TestCapabilitiesResponse:
    """Test CapabilitiesResponse schema."""

    def test_core_edition_response(self) -> None:
        """Test creating a core edition response."""
        providers = ProviderConfig(
            history=ProviderType.NONE,
            evidence=ProviderType.NONE,
            crypto=ProviderType.NONE,
        )
        features = FeatureFlags()

        response = CapabilitiesResponse(
            edition=Edition.CORE,
            stateful_enabled=False,
            providers=providers,
            features=features,
            capabilities={
                "basic_analytics": True,
                "run_manifests": True,
                "conversation_storage": False,
                "cross_user_analytics": False,
            },
            version="1.0.0",
            build_info={"build_date": "2024-01-01", "git_commit": "abc123"},
        )

        assert response.edition == Edition.CORE
        assert response.stateful_enabled is False
        assert response.providers == providers
        assert response.features == features
        assert response.capabilities["basic_analytics"] is True
        assert response.capabilities["conversation_storage"] is False
        assert response.version == "1.0.0"
        assert response.build_info == {
            "build_date": "2024-01-01",
            "git_commit": "abc123",
        }

    def test_plus_edition_response(self) -> None:
        """Test creating a plus edition response."""
        providers = ProviderConfig(
            history=ProviderType.GOVERNED,
            evidence=ProviderType.GOVERNED,
            crypto=ProviderType.GOVERNED,
        )
        features = FeatureFlags(expert_chunking=True, advanced_analytics=True)

        response = CapabilitiesResponse(
            edition=Edition.PLUS,
            stateful_enabled=True,
            providers=providers,
            features=features,
            capabilities={
                "basic_analytics": True,
                "run_manifests": True,
                "conversation_storage": True,
                "cross_user_analytics": True,
            },
            version="2.0.0",
        )

        assert response.edition == Edition.PLUS
        assert response.stateful_enabled is True
        assert response.capabilities["conversation_storage"] is True
        assert response.capabilities["cross_user_analytics"] is True

    def test_capabilities_validation_core_stateful(self) -> None:
        """Test that core edition cannot have stateful capabilities."""
        providers = ProviderConfig(
            history=ProviderType.NONE,
            evidence=ProviderType.NONE,
            crypto=ProviderType.NONE,
        )
        features = FeatureFlags()

        with pytest.raises(
            ValueError, match="Core edition cannot have conversation_storage capability"
        ):
            CapabilitiesResponse(
                edition=Edition.CORE,
                stateful_enabled=False,
                providers=providers,
                features=features,
                capabilities={
                    "conversation_storage": True,  # Not allowed for core
                },
                version="1.0.0",
            )

    def test_capabilities_validation_no_history_provider(self) -> None:
        """Test that no history provider means no conversation storage."""
        providers = ProviderConfig(
            history=ProviderType.NONE,  # No history provider
            evidence=ProviderType.NONE,
            crypto=ProviderType.NONE,
        )
        features = FeatureFlags()

        with pytest.raises(
            ValueError,
            match="No history provider means no conversation storage capability",
        ):
            CapabilitiesResponse(
                edition=Edition.PLUS,
                stateful_enabled=True,
                providers=providers,
                features=features,
                capabilities={
                    "conversation_storage": True,  # Not allowed without history provider
                },
                version="2.0.0",
            )

    def test_default_build_info(self) -> None:
        """Test default build info."""
        providers = ProviderConfig(
            history=ProviderType.NONE,
            evidence=ProviderType.NONE,
            crypto=ProviderType.NONE,
        )
        features = FeatureFlags()

        response = CapabilitiesResponse(
            edition=Edition.CORE,
            stateful_enabled=False,
            providers=providers,
            features=features,
            capabilities={"basic_analytics": True},
            version="1.0.0",
        )

        assert response.build_info == {}


class TestCapabilityRequest:
    """Test CapabilityRequest schema."""

    def test_specific_capability_request(self) -> None:
        """Test requesting a specific capability."""
        request = CapabilityRequest(
            capability_name="conversation_storage",
            include_experimental=True,
            include_deprecated=False,
        )

        assert request.capability_name == "conversation_storage"
        assert request.include_experimental is True
        assert request.include_deprecated is False

    def test_general_capability_request(self) -> None:
        """Test requesting all capabilities."""
        request = CapabilityRequest()

        assert request.capability_name is None
        assert request.include_experimental is False
        assert request.include_deprecated is False


class TestCapabilityDetails:
    """Test CapabilityDetails schema."""

    def test_valid_capability_details(self) -> None:
        """Test creating valid capability details."""
        details = CapabilityDetails(
            name="advanced_analytics",
            status=CapabilityStatus.AVAILABLE,
            description="Advanced analytics with ML insights",
            edition_required=Edition.PLUS,
            provider_required=ProviderType.GOVERNED,
            dependencies=["conversation_storage", "run_manifests"],
            configuration={"ml_models": ["sentiment", "classification"]},
            examples=["Get sentiment analysis", "Classify conversations"],
            limitations=["Requires 1GB+ RAM", "GPU recommended"],
        )

        assert details.name == "advanced_analytics"
        assert details.status == CapabilityStatus.AVAILABLE
        assert details.description == "Advanced analytics with ML insights"
        assert details.edition_required == Edition.PLUS
        assert details.provider_required == ProviderType.GOVERNED
        assert details.dependencies == ["conversation_storage", "run_manifests"]
        assert details.configuration == {"ml_models": ["sentiment", "classification"]}
        assert details.examples == ["Get sentiment analysis", "Classify conversations"]
        assert details.limitations == ["Requires 1GB+ RAM", "GPU recommended"]

    def test_default_values(self) -> None:
        """Test default values."""
        details = CapabilityDetails(
            name="basic_analytics",
            status=CapabilityStatus.AVAILABLE,
            description="Basic analytics",
            edition_required=Edition.CORE,
        )

        assert details.provider_required is None
        assert details.dependencies == []
        assert details.configuration == {}
        assert details.examples == []
        assert details.limitations == []


class TestSystemInfo:
    """Test SystemInfo schema."""

    def test_valid_system_info(self) -> None:
        """Test creating valid system info."""
        info = SystemInfo(
            version="1.0.0",
            edition=Edition.CORE,
            build_date="2024-01-01",
            git_commit="abc123def456",
            environment="production",
            features_enabled=["run_manifests", "basic_analytics"],
            providers_configured=["history", "evidence"],
        )

        assert info.version == "1.0.0"
        assert info.edition == Edition.CORE
        assert info.build_date == "2024-01-01"
        assert info.git_commit == "abc123def456"
        assert info.environment == "production"
        assert info.features_enabled == ["run_manifests", "basic_analytics"]
        assert info.providers_configured == ["history", "evidence"]

    def test_optional_git_commit(self) -> None:
        """Test optional git commit."""
        info = SystemInfo(
            version="1.0.0",
            edition=Edition.CORE,
            build_date="2024-01-01",
            environment="development",
        )

        assert info.git_commit is None
        assert info.features_enabled == []
        assert info.providers_configured == []


class TestCapabilityHealthCheck:
    """Test CapabilityHealthCheck schema."""

    def test_healthy_capability(self) -> None:
        """Test creating a healthy capability check."""
        check = CapabilityHealthCheck(
            capability_name="run_manifests",
            healthy=True,
            check_time="2024-01-01T12:00:00Z",
            response_time_ms=50,
            error_message=None,
            details={"status": "ok", "version": "1.0.0"},
        )

        assert check.capability_name == "run_manifests"
        assert check.healthy is True
        assert check.check_time == "2024-01-01T12:00:00Z"
        assert check.response_time_ms == 50
        assert check.error_message is None
        assert check.details == {"status": "ok", "version": "1.0.0"}

    def test_unhealthy_capability(self) -> None:
        """Test creating an unhealthy capability check."""
        check = CapabilityHealthCheck(
            capability_name="conversation_storage",
            healthy=False,
            check_time="2024-01-01T12:00:00Z",
            response_time_ms=5000,
            error_message="Service unavailable",
            details={"error": "timeout", "retry_count": 3},
        )

        assert check.healthy is False
        assert check.error_message == "Service unavailable"
        assert check.details == {"error": "timeout", "retry_count": 3}

    def test_default_details(self) -> None:
        """Test default details."""
        check = CapabilityHealthCheck(
            capability_name="basic_analytics",
            healthy=True,
            check_time="2024-01-01T12:00:00Z",
            response_time_ms=100,
        )

        assert check.details == {}


class TestCapabilityMetrics:
    """Test CapabilityMetrics schema."""

    def test_valid_metrics(self) -> None:
        """Test creating valid capability metrics."""
        metrics = CapabilityMetrics(
            capability_name="run_manifests",
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            avg_response_time_ms=120.5,
            error_rate=0.05,
            last_request_at="2024-01-01T12:00:00Z",
            throughput_per_minute=10.5,
        )

        assert metrics.capability_name == "run_manifests"
        assert metrics.total_requests == 1000
        assert metrics.successful_requests == 950
        assert metrics.failed_requests == 50
        assert metrics.avg_response_time_ms == 120.5
        assert metrics.error_rate == 0.05
        assert metrics.last_request_at == "2024-01-01T12:00:00Z"
        assert metrics.throughput_per_minute == 10.5

    def test_default_values(self) -> None:
        """Test default values."""
        metrics = CapabilityMetrics(capability_name="test_capability")

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.avg_response_time_ms == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.last_request_at is None
        assert metrics.throughput_per_minute == 0.0

    def test_error_rate_validation(self) -> None:
        """Test error rate validation."""
        with pytest.raises(ValueError):
            CapabilityMetrics(
                capability_name="test",
                error_rate=-0.1,  # < 0.0
            )

        with pytest.raises(ValueError):
            CapabilityMetrics(
                capability_name="test",
                error_rate=1.5,  # > 1.0
            )
