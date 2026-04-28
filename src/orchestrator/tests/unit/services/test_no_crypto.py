"""Unit tests for NoCrypto provider."""

from typing import cast

import pytest
from app.services.providers.no_crypto import NoCrypto


class TestNoCrypto:
    """Test NoCrypto provider."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = NoCrypto()
        assert provider.provider_type == "none"
        assert provider.enabled is True

    @pytest.mark.asyncio
    async def test_encrypt_passthrough(self) -> None:
        """Test encrypt method passes data through unchanged."""
        provider = NoCrypto()
        data = "sensitive data to encrypt"

        result = await provider.encrypt(data)
        assert result == data

    @pytest.mark.asyncio
    async def test_decrypt_passthrough(self) -> None:
        """Test decrypt method passes data through unchanged."""
        provider = NoCrypto()
        encrypted_data = "encrypted data"

        result = await provider.decrypt(encrypted_data)
        assert result == encrypted_data

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_cycle(self) -> None:
        """Test encrypt-decrypt cycle."""
        provider = NoCrypto()
        original_data = "original sensitive data"

        # Encrypt
        encrypted = await provider.encrypt(original_data)
        assert encrypted == original_data

        # Decrypt
        decrypted = await provider.decrypt(encrypted)
        assert decrypted == original_data

    @pytest.mark.asyncio
    async def test_different_data_types(self) -> None:
        """Test with different data types."""
        provider = NoCrypto()

        # Test various data types
        test_cases = [
            "simple string",
            "string with special chars: !@#$%^&*()",
            "unicode: 你好世界",
            "numbers: 123456789",
            'json-like: {"key": "value"}',
            "empty string",
            "very long string " * 100,
        ]

        for data in test_cases:
            encrypted = await provider.encrypt(data)
            decrypted = await provider.decrypt(encrypted)
            assert encrypted == data
            assert decrypted == data

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        provider = NoCrypto()

        health = await provider.health_check()
        assert health["provider_type"] == "none"
        assert health["enabled"] is True
        assert health["healthy"] is True
        assert "no encryption" in health["message"]

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get stats."""
        provider = NoCrypto()

        stats = await provider.get_stats()
        assert stats["provider_type"] == "none"
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_string_representation(self) -> None:
        """Test string representation."""
        provider = NoCrypto()

        str_repr = str(provider)
        assert "NoCrypto" in str_repr
        assert "none" in str_repr
        assert "True" in str_repr

        repr_str = repr(provider)
        assert "NoCrypto" in repr_str
        assert "none" in repr_str
        assert "True" in repr_str

    @pytest.mark.asyncio
    async def test_multiple_operations(self) -> None:
        """Test multiple operations."""
        provider = NoCrypto()

        # Multiple encrypt/decrypt operations
        for i in range(10):
            data = f"test data {i}"
            encrypted = await provider.encrypt(data)
            decrypted = await provider.decrypt(encrypted)
            assert encrypted == data
            assert decrypted == data

        # Stats should still be zero
        stats = await provider.get_stats()
        assert stats["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_edge_cases(self) -> None:
        """Test edge cases."""
        provider = NoCrypto()

        # None data
        result = await provider.encrypt(None)
        assert result is None

        result = await provider.decrypt(None)
        assert result is None

        # Empty string
        result = await provider.encrypt("")
        assert result == ""

        result = await provider.decrypt("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self) -> None:
        """Test concurrent operations."""
        import asyncio

        provider = NoCrypto()

        async def encrypt_data(data: str) -> str:
            return cast("str", await provider.encrypt(data))

        async def decrypt_data(data: str) -> str:
            return cast("str", await provider.decrypt(data))

        # Run multiple operations concurrently
        tasks = []
        for i in range(5):
            data = f"concurrent data {i}"
            tasks.append(encrypt_data(data))
            tasks.append(decrypt_data(data))

        results = await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert len(results) == 10
        for result in results:
            assert isinstance(result, str)
