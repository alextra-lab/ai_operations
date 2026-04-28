"""Unit tests for NoneEvidence provider."""

import pytest
from app.services.providers.none_evidence import NoneEvidence


class TestNoneEvidence:
    """Test NoneEvidence provider."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = NoneEvidence()
        assert provider.sink_type == "none"
        assert provider.enabled is True

    @pytest.mark.asyncio
    async def test_store_returns_dummy_id(self) -> None:
        """Test store method returns dummy ID."""
        provider = NoneEvidence()
        evidence = {"type": "screenshot", "data": "base64data"}

        evidence_id = await provider.store(evidence)
        assert isinstance(evidence_id, str)
        assert len(evidence_id) > 0  # Should be a UUID string

    @pytest.mark.asyncio
    async def test_store_different_evidence_types(self) -> None:
        """Test store with different evidence types."""
        provider = NoneEvidence()

        # Test various evidence types
        id1 = await provider.store({"type": "screenshot", "data": "data1"})
        id2 = await provider.store({"type": "log", "content": "log data"})
        id3 = await provider.store({"type": "document", "file": "file.pdf"})

        # All should return different dummy IDs
        assert id1 != id2 != id3
        assert all(isinstance(id_val, str) for id_val in [id1, id2, id3])

    @pytest.mark.asyncio
    async def test_retrieve_returns_empty(self) -> None:
        """Test retrieve method returns empty dict."""
        provider = NoneEvidence()

        result = await provider.retrieve("any-id")
        assert result == {}

        # Test with different IDs
        result = await provider.retrieve("non-existent-id")
        assert result == {}

        result = await provider.retrieve("")
        assert result == {}

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        provider = NoneEvidence()

        health = await provider.health_check()
        assert health["sink_type"] == "none"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "no server-side storage" in health["message"]

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        provider = NoneEvidence()

        stats = await provider.get_stats()
        assert stats["sink_type"] == "none"
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        provider = NoneEvidence()

        str_repr = str(provider)
        assert "NoneEvidence" in str_repr
        assert "none" in str_repr
        assert "True" in str_repr

        repr_str = repr(provider)
        assert "NoneEvidence" in repr_str
        assert "none" in repr_str
        assert "True" in repr_str

    @pytest.mark.asyncio
    async def test_store_retrieve_cycle(self) -> None:
        """Test store and retrieve cycle."""
        provider = NoneEvidence()

        # Store evidence
        evidence = {"type": "test", "data": "test_data"}
        evidence_id = await provider.store(evidence)

        # Retrieve should return empty (no-op)
        retrieved = await provider.retrieve(evidence_id)
        assert retrieved == {}

    @pytest.mark.asyncio
    async def test_multiple_operations(self) -> None:
        """Test multiple operations."""
        provider = NoneEvidence()

        # Multiple stores
        ids = []
        for i in range(5):
            evidence = {"test": f"data_{i}"}
            evidence_id = await provider.store(evidence)
            ids.append(evidence_id)

        # All should return different dummy IDs
        assert len(set(ids)) == 5

        # Stats should still be zero
        stats = await provider.get_stats()
        assert stats["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_empty_evidence(self) -> None:
        """Test store with empty evidence."""
        provider = NoneEvidence()

        # Empty evidence
        evidence_id = await provider.store({})
        assert isinstance(evidence_id, str)

        # None evidence
        evidence_id = await provider.store(None)
        assert isinstance(evidence_id, str)
