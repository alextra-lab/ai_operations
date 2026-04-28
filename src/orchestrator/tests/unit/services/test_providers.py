"""Unit tests for provider services."""

from uuid import uuid4

import pytest

from src.orchestrator.app.services.providers import (
    EdgeOnlyHistory,
    NoCrypto,
    NoneEvidence,
    create_crypto_provider,
    create_evidence_sink,
    create_history_provider,
    create_providers,
)


class TestEdgeOnlyHistory:
    """Test EdgeOnlyHistory provider."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = EdgeOnlyHistory()

        assert provider.provider_type == "edge_only"
        assert provider.enabled is True

    @pytest.mark.asyncio
    async def test_append_no_op(self) -> None:
        """Test that append is a no-op."""
        provider = EdgeOnlyHistory()
        run_id = uuid4()
        payload = {"message": "test"}

        # Should not raise any exceptions
        await provider.append(run_id, payload)

    @pytest.mark.asyncio
    async def test_fetch_returns_empty(self) -> None:
        """Test that fetch returns empty list."""
        provider = EdgeOnlyHistory()
        run_id = uuid4()

        result = await provider.fetch(case_id="test-case", run_id=run_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_with_none_params(self) -> None:
        """Test fetch with None parameters."""
        provider = EdgeOnlyHistory()

        result = await provider.fetch()

        assert result == []

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        provider = EdgeOnlyHistory()

        health = await provider.health_check()

        assert health["provider_type"] == "edge_only"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "message" in health

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        provider = EdgeOnlyHistory()

        stats = await provider.get_stats()

        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        provider = EdgeOnlyHistory()

        str_repr = str(provider)
        repr_str = repr(provider)

        assert "EdgeOnlyHistory" in str_repr
        assert "edge_only" in str_repr
        assert "EdgeOnlyHistory" in repr_str
        assert "edge_only" in repr_str


class TestNoneEvidence:
    """Test NoneEvidence sink."""

    def test_initialization(self) -> None:
        """Test sink initialization."""
        sink = NoneEvidence()

        assert sink.sink_type == "none"
        assert sink.enabled is True

    @pytest.mark.asyncio
    async def test_store_returns_dummy_id(self) -> None:
        """Test that store returns a dummy ID."""
        sink = NoneEvidence()
        evidence = {"data": "test"}

        evidence_id = await sink.store(evidence)

        assert evidence_id is not None
        assert len(evidence_id) > 0

    @pytest.mark.asyncio
    async def test_retrieve_returns_empty(self) -> None:
        """Test that retrieve returns empty dict."""
        sink = NoneEvidence()

        result = await sink.retrieve("dummy-id")

        assert result == {}

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        sink = NoneEvidence()

        health = await sink.health_check()

        assert health["sink_type"] == "none"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "message" in health

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        sink = NoneEvidence()

        stats = await sink.get_stats()

        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        sink = NoneEvidence()

        str_repr = str(sink)
        repr_str = repr(sink)

        assert "NoneEvidence" in str_repr
        assert "none" in str_repr
        assert "NoneEvidence" in repr_str
        assert "none" in repr_str


class TestNoCrypto:
    """Test NoCrypto provider."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = NoCrypto()

        assert provider.provider_type == "none"
        assert provider.enabled is True

    @pytest.mark.asyncio
    async def test_encrypt_passes_through(self) -> None:
        """Test that encrypt passes data through unchanged."""
        provider = NoCrypto()
        data = "test data"

        result = await provider.encrypt(data)

        assert result == data

    @pytest.mark.asyncio
    async def test_decrypt_passes_through(self) -> None:
        """Test that decrypt passes data through unchanged."""
        provider = NoCrypto()
        encrypted_data = "encrypted data"

        result = await provider.decrypt(encrypted_data)

        assert result == encrypted_data

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        provider = NoCrypto()

        health = await provider.health_check()

        assert health["provider_type"] == "none"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "message" in health

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        provider = NoCrypto()

        stats = await provider.get_stats()

        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        provider = NoCrypto()

        str_repr = str(provider)
        repr_str = repr(provider)

        assert "NoCrypto" in str_repr
        assert "none" in str_repr
        assert "NoCrypto" in repr_str
        assert "none" in repr_str


class TestCreateProviders:
    """Test create_providers function."""

    def test_create_providers_returns_no_ops(self) -> None:
        """Test that create_providers returns no-op providers."""
        history, evidence, crypto = create_providers()

        assert isinstance(history, EdgeOnlyHistory)
        assert isinstance(evidence, NoneEvidence)
        assert isinstance(crypto, NoCrypto)

    def test_create_providers_always_no_ops(self) -> None:
        """Test that create_providers always returns no-ops for v1."""
        # Test with different configurations
        history1, evidence1, crypto1 = create_providers()
        history2, evidence2, crypto2 = create_providers()

        assert isinstance(history1, EdgeOnlyHistory)
        assert isinstance(evidence1, NoneEvidence)
        assert isinstance(crypto1, NoCrypto)

        assert isinstance(history2, EdgeOnlyHistory)
        assert isinstance(evidence2, NoneEvidence)
        assert isinstance(crypto2, NoCrypto)


class TestCreateHistoryProvider:
    """Test create_history_provider function."""

    def test_create_history_provider_none(self) -> None:
        """Test creating history provider with 'none' type."""
        provider = create_history_provider("none")

        assert isinstance(provider, EdgeOnlyHistory)

    def test_create_history_provider_governed(self) -> None:
        """Test creating history provider with 'governed' type (future)."""
        # For now, should still return EdgeOnlyHistory
        provider = create_history_provider("governed")

        assert isinstance(provider, EdgeOnlyHistory)

    def test_create_history_provider_unknown(self) -> None:
        """Test creating history provider with unknown type."""
        # Should default to EdgeOnlyHistory
        provider = create_history_provider("unknown")

        assert isinstance(provider, EdgeOnlyHistory)


class TestCreateEvidenceSink:
    """Test create_evidence_sink function."""

    def test_create_evidence_sink_none(self) -> None:
        """Test creating evidence sink with 'none' type."""
        sink = create_evidence_sink("none")

        assert isinstance(sink, NoneEvidence)

    def test_create_evidence_sink_governed(self) -> None:
        """Test creating evidence sink with 'governed' type (future)."""
        # For now, should still return NoneEvidence
        sink = create_evidence_sink("governed")

        assert isinstance(sink, NoneEvidence)

    def test_create_evidence_sink_unknown(self) -> None:
        """Test creating evidence sink with unknown type."""
        # Should default to NoneEvidence
        sink = create_evidence_sink("unknown")

        assert isinstance(sink, NoneEvidence)


class TestCreateCryptoProvider:
    """Test create_crypto_provider function."""

    def test_create_crypto_provider_none(self) -> None:
        """Test creating crypto provider with 'none' type."""
        provider = create_crypto_provider("none")

        assert isinstance(provider, NoCrypto)

    def test_create_crypto_provider_kms(self) -> None:
        """Test creating crypto provider with 'kms' type (future)."""
        # For now, should still return NoCrypto
        provider = create_crypto_provider("kms")

        assert isinstance(provider, NoCrypto)

    def test_create_crypto_provider_unknown(self) -> None:
        """Test creating crypto provider with unknown type."""
        # Should default to NoCrypto
        provider = create_crypto_provider("unknown")

        assert isinstance(provider, NoCrypto)


class TestProviderIntegration:
    """Test provider integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_provider_workflow(self) -> None:
        """Test a complete workflow using all providers."""
        # Create providers
        history, evidence, crypto = create_providers()

        # Test history operations
        run_id = uuid4()
        await history.append(run_id, {"message": "test"})
        history_entries = await history.fetch(run_id=run_id)
        assert history_entries == []

        # Test evidence operations
        evidence_id = await evidence.store({"data": "test"})
        assert evidence_id is not None
        retrieved_evidence = await evidence.retrieve(evidence_id)
        assert retrieved_evidence == {}

        # Test crypto operations
        original_data = "sensitive data"
        encrypted = await crypto.encrypt(original_data)
        decrypted = await crypto.decrypt(encrypted)
        assert decrypted == original_data

    @pytest.mark.asyncio
    async def test_provider_health_checks(self) -> None:
        """Test health checks for all providers."""
        history, evidence, crypto = create_providers()

        # Test all health checks
        history_health = await history.health_check()  # type: ignore[attr-defined]
        evidence_health = await evidence.health_check()  # type: ignore[attr-defined]
        crypto_health = await crypto.health_check()  # type: ignore[attr-defined]

        assert history_health["healthy"] is True
        assert evidence_health["healthy"] is True
        assert crypto_health["healthy"] is True

    @pytest.mark.asyncio
    async def test_provider_stats(self) -> None:
        """Test stats for all providers."""
        history, evidence, crypto = create_providers()

        # Test all stats
        history_stats = await history.get_stats()  # type: ignore[attr-defined]
        evidence_stats = await evidence.get_stats()  # type: ignore[attr-defined]
        crypto_stats = await crypto.get_stats()  # type: ignore[attr-defined]

        assert history_stats["total_operations"] == 0
        assert evidence_stats["total_operations"] == 0
        assert crypto_stats["total_operations"] == 0
