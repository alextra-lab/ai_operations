"""Unit tests for EdgeOnlyHistory provider."""

from uuid import uuid4

import pytest
from app.services.providers.edge_only_history import EdgeOnlyHistory


class TestEdgeOnlyHistory:
    """Test EdgeOnlyHistory provider."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = EdgeOnlyHistory()
        assert provider.provider_type == "edge_only"
        assert provider.enabled is True

    @pytest.mark.asyncio
    async def test_append_no_op(self) -> None:
        """Test append method (no-op)."""
        provider = EdgeOnlyHistory()
        run_id = uuid4()
        payload = {"message": "test", "timestamp": "2025-01-01T00:00:00Z"}

        # Should not raise any exceptions
        await provider.append(run_id, payload)

    @pytest.mark.asyncio
    async def test_fetch_empty(self) -> None:
        """Test fetch method returns empty list."""
        provider = EdgeOnlyHistory()

        result = await provider.fetch()
        assert result == []

        result = await provider.fetch(case_id="test-case")
        assert result == []

        result = await provider.fetch(run_id=uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        provider = EdgeOnlyHistory()

        health = await provider.health_check()
        assert health["provider_type"] == "edge_only"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "no server-side storage" in health["message"]

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        provider = EdgeOnlyHistory()

        stats = await provider.get_stats()
        assert stats["provider_type"] == "edge_only"
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        provider = EdgeOnlyHistory()

        str_repr = str(provider)
        assert "EdgeOnlyHistory" in str_repr
        assert "edge_only" in str_repr
        assert "True" in str_repr

        repr_str = repr(provider)
        assert "EdgeOnlyHistory" in repr_str
        assert "edge_only" in repr_str
        assert "True" in repr_str

    @pytest.mark.asyncio
    async def test_multiple_operations(self) -> None:
        """Test multiple operations don't affect each other."""
        provider = EdgeOnlyHistory()

        # Multiple appends
        for i in range(5):
            await provider.append(uuid4(), {"test": f"data_{i}"})

        # Fetch should still return empty
        result = await provider.fetch()
        assert result == []

        # Stats should still be zero
        stats = await provider.get_stats()
        assert stats["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_different_payload_types(self) -> None:
        """Test append with different payload types."""
        provider = EdgeOnlyHistory()

        # Test with various payload types
        await provider.append(uuid4(), {"simple": "data"})
        await provider.append(uuid4(), {"complex": {"nested": "data"}})
        await provider.append(uuid4(), {"list": [1, 2, 3]})
        await provider.append(uuid4(), {})  # Empty payload

        # All should work without errors
        result = await provider.fetch()
        assert result == []
