"""Unit tests for provider interface schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from app.schemas.provider_interfaces import (
    CryptoOperation,
    EvidenceEntry,
    HistoryEntry,
    ProviderConfig,
    ProviderHealthCheck,
    ProviderMetrics,
    ProviderStatus,
    ProviderType,
)


class TestProviderType:
    """Test ProviderType enum."""

    def test_provider_type_values(self) -> None:
        """Test that ProviderType has correct values."""
        assert ProviderType.NONE == "none"
        assert ProviderType.GOVERNED == "governed"


class TestProviderConfig:
    """Test ProviderConfig schema."""

    def test_valid_config(self) -> None:
        """Test creating a valid provider config."""
        config = ProviderConfig(
            provider_type=ProviderType.GOVERNED,
            enabled=True,
            config={"key": "value"},
            timeout_seconds=60,
            retry_attempts=5,
            retry_delay_ms=2000,
        )

        assert config.provider_type == ProviderType.GOVERNED
        assert config.enabled is True
        assert config.config == {"key": "value"}
        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5
        assert config.retry_delay_ms == 2000

    def test_default_values(self) -> None:
        """Test default values."""
        config = ProviderConfig(provider_type=ProviderType.NONE)

        assert config.enabled is True
        assert config.config == {}
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.retry_delay_ms == 1000

    def test_timeout_validation(self) -> None:
        """Test timeout validation."""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                timeout_seconds=0,  # < 1
            )

        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                timeout_seconds=400,  # > 300
            )

    def test_retry_validation(self) -> None:
        """Test retry validation."""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                retry_attempts=-1,  # < 0
            )

        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                retry_attempts=15,  # > 10
            )

    def test_retry_delay_validation(self) -> None:
        """Test retry delay validation."""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                retry_delay_ms=50,  # < 100
            )

        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.NONE,
                retry_delay_ms=15000,  # > 10000
            )


class TestHistoryEntry:
    """Test HistoryEntry schema."""

    def test_valid_entry(self) -> None:
        """Test creating a valid history entry."""
        run_id = uuid4()
        now = datetime.utcnow()

        entry = HistoryEntry(
            run_id=run_id,
            case_id="test-case-1",
            timestamp=now,
            entry_type="conversation",
            content={"message": "Hello world"},
            metadata={"source": "user"},
        )

        assert entry.run_id == run_id
        assert entry.case_id == "test-case-1"
        assert entry.timestamp == now
        assert entry.entry_type == "conversation"
        assert entry.content == {"message": "Hello world"}
        assert entry.metadata == {"source": "user"}

    def test_optional_case_id(self) -> None:
        """Test optional case_id."""
        run_id = uuid4()
        now = datetime.utcnow()

        entry = HistoryEntry(
            run_id=run_id,
            timestamp=now,
            entry_type="system",
            content={"status": "ready"},
        )

        assert entry.case_id is None
        assert entry.metadata == {}

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        run_id = uuid4()
        now = datetime.utcnow()

        entry = HistoryEntry(
            run_id=run_id,
            timestamp=now,
            entry_type="test",
            content={"data": "value"},
        )

        # Test that the Config is properly set
        assert entry.Config.from_attributes is True
        assert "json_encoders" in entry.Config.__dict__


class TestEvidenceEntry:
    """Test EvidenceEntry schema."""

    def test_valid_entry(self) -> None:
        """Test creating a valid evidence entry."""
        now = datetime.utcnow()
        expires = datetime(2024, 12, 31)

        entry = EvidenceEntry(
            evidence_id="evid-123",
            evidence_type="document",
            content={"title": "Test Document", "content": "Test content"},
            metadata={"author": "test-user"},
            created_at=now,
            expires_at=expires,
        )

        assert entry.evidence_id == "evid-123"
        assert entry.evidence_type == "document"
        assert entry.content == {"title": "Test Document", "content": "Test content"}
        assert entry.metadata == {"author": "test-user"}
        assert entry.created_at == now
        assert entry.expires_at == expires

    def test_optional_expires_at(self) -> None:
        """Test optional expires_at."""
        now = datetime.utcnow()

        entry = EvidenceEntry(
            evidence_id="evid-123",
            evidence_type="document",
            content={"title": "Test Document"},
            created_at=now,
        )

        assert entry.expires_at is None

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        now = datetime.utcnow()

        entry = EvidenceEntry(
            evidence_id="evid-123",
            evidence_type="document",
            content={"title": "Test Document"},
            created_at=now,
        )

        # Test that the Config is properly set
        assert entry.Config.from_attributes is True
        assert "json_encoders" in entry.Config.__dict__


class TestCryptoOperation:
    """Test CryptoOperation schema."""

    def test_valid_operation(self) -> None:
        """Test creating a valid crypto operation."""
        now = datetime.utcnow()

        operation = CryptoOperation(
            operation_id="op-123",
            operation_type="encrypt",
            data_size=1024,
            algorithm="AES-256",
            key_id="key-456",
            timestamp=now,
            success=True,
            error_message=None,
        )

        assert operation.operation_id == "op-123"
        assert operation.operation_type == "encrypt"
        assert operation.data_size == 1024
        assert operation.algorithm == "AES-256"
        assert operation.key_id == "key-456"
        assert operation.timestamp == now
        assert operation.success is True
        assert operation.error_message is None

    def test_failed_operation(self) -> None:
        """Test creating a failed operation."""
        now = datetime.utcnow()

        operation = CryptoOperation(
            operation_id="op-124",
            operation_type="decrypt",
            data_size=512,
            algorithm="AES-256",
            key_id=None,
            timestamp=now,
            success=False,
            error_message="Invalid key",
        )

        assert operation.success is False
        assert operation.error_message == "Invalid key"
        assert operation.key_id is None

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        now = datetime.utcnow()

        operation = CryptoOperation(
            operation_id="op-123",
            operation_type="encrypt",
            data_size=1024,
            algorithm="AES-256",
            timestamp=now,
            success=True,
        )

        # Test that the Config is properly set
        assert operation.Config.from_attributes is True
        assert "json_encoders" in operation.Config.__dict__


class TestProviderStatus:
    """Test ProviderStatus schema."""

    def test_healthy_status(self) -> None:
        """Test creating a healthy provider status."""
        now = datetime.utcnow()

        status = ProviderStatus(
            provider_type="history",
            enabled=True,
            healthy=True,
            last_check=now,
            error_count=0,
            response_time_ms=50,
            error_message=None,
        )

        assert status.provider_type == "history"
        assert status.enabled is True
        assert status.healthy is True
        assert status.last_check == now
        assert status.error_count == 0
        assert status.response_time_ms == 50
        assert status.error_message is None

    def test_unhealthy_status(self) -> None:
        """Test creating an unhealthy provider status."""
        now = datetime.utcnow()

        status = ProviderStatus(
            provider_type="evidence",
            enabled=True,
            healthy=False,
            last_check=now,
            error_count=5,
            response_time_ms=None,
            error_message="Connection timeout",
        )

        assert status.healthy is False
        assert status.error_count == 5
        assert status.response_time_ms is None
        assert status.error_message == "Connection timeout"

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        now = datetime.utcnow()

        status = ProviderStatus(
            provider_type="crypto",
            enabled=True,
            healthy=True,
            last_check=now,
        )

        # Test that the Config is properly set
        assert status.Config.from_attributes is True
        assert "json_encoders" in status.Config.__dict__


class TestProviderMetrics:
    """Test ProviderMetrics schema."""

    def test_valid_metrics(self) -> None:
        """Test creating valid provider metrics."""
        now = datetime.utcnow()

        metrics = ProviderMetrics(
            provider_type="history",
            total_operations=1000,
            successful_operations=950,
            failed_operations=50,
            avg_response_time_ms=120.5,
            min_response_time_ms=50,
            max_response_time_ms=500,
            error_rate=0.05,
            last_operation_at=now,
        )

        assert metrics.provider_type == "history"
        assert metrics.total_operations == 1000
        assert metrics.successful_operations == 950
        assert metrics.failed_operations == 50
        assert metrics.avg_response_time_ms == 120.5
        assert metrics.min_response_time_ms == 50
        assert metrics.max_response_time_ms == 500
        assert metrics.error_rate == 0.05
        assert metrics.last_operation_at == now

    def test_default_values(self) -> None:
        """Test default values."""
        metrics = ProviderMetrics(provider_type="crypto")

        assert metrics.total_operations == 0
        assert metrics.successful_operations == 0
        assert metrics.failed_operations == 0
        assert metrics.avg_response_time_ms == 0.0
        assert metrics.min_response_time_ms == 0
        assert metrics.max_response_time_ms == 0
        assert metrics.error_rate == 0.0
        assert metrics.last_operation_at is None

    def test_error_rate_validation(self) -> None:
        """Test error rate validation."""
        with pytest.raises(ValueError):
            ProviderMetrics(
                provider_type="test",
                error_rate=-0.1,  # < 0.0
            )

        with pytest.raises(ValueError):
            ProviderMetrics(
                provider_type="test",
                error_rate=1.5,  # > 1.0
            )

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        metrics = ProviderMetrics(provider_type="test")

        # Test that the Config is properly set
        assert metrics.Config.from_attributes is True
        assert "json_encoders" in metrics.Config.__dict__


class TestProviderHealthCheck:
    """Test ProviderHealthCheck schema."""

    def test_healthy_check(self) -> None:
        """Test creating a healthy provider check."""
        now = datetime.utcnow()

        check = ProviderHealthCheck(
            provider_type="history",
            healthy=True,
            check_time=now,
            response_time_ms=25,
            error_message=None,
            details={"status": "ok", "version": "1.0.0"},
        )

        assert check.provider_type == "history"
        assert check.healthy is True
        assert check.check_time == now
        assert check.response_time_ms == 25
        assert check.error_message is None
        assert check.details == {"status": "ok", "version": "1.0.0"}

    def test_unhealthy_check(self) -> None:
        """Test creating an unhealthy provider check."""
        now = datetime.utcnow()

        check = ProviderHealthCheck(
            provider_type="evidence",
            healthy=False,
            check_time=now,
            response_time_ms=5000,
            error_message="Service unavailable",
            details={"error": "timeout", "retry_count": 3},
        )

        assert check.healthy is False
        assert check.response_time_ms == 5000
        assert check.error_message == "Service unavailable"
        assert check.details == {"error": "timeout", "retry_count": 3}

    def test_default_details(self) -> None:
        """Test default details."""
        now = datetime.utcnow()

        check = ProviderHealthCheck(
            provider_type="crypto",
            healthy=True,
            check_time=now,
            response_time_ms=100,
        )

        assert check.details == {}

    def test_json_encoding(self) -> None:
        """Test JSON encoding configuration."""
        now = datetime.utcnow()

        check = ProviderHealthCheck(
            provider_type="test",
            healthy=True,
            check_time=now,
            response_time_ms=50,
        )

        # Test that the Config is properly set
        assert check.Config.from_attributes is True
        assert "json_encoders" in check.Config.__dict__
