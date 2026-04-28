"""
No Crypto Provider for Stateless Core v1

This provider implements the CryptoProvider protocol but doesn't perform
actual cryptographic operations. Data is passed through unchanged.

This aligns with ADR-033 (Provider Interfaces) for the stateless architecture.
"""

from typing import Any

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


class NoCrypto:
    """
    No-op crypto provider for stateless v1.

    This provider doesn't perform actual cryptographic operations.
    Data is passed through unchanged for stateless architecture.
    """

    def __init__(self) -> None:
        """Initialize the no crypto provider."""
        self.provider_type = "none"
        self.enabled = True
        logger.info("Initialized NoCrypto provider (no encryption)")

    async def encrypt(self, data: str) -> str:
        """
        No-op: return data as-is.

        Args:
            data: Data to encrypt (passed through unchanged)

        Returns:
            Data unchanged (no encryption)
        """
        logger.debug("NoCrypto.encrypt called (no-op)")
        # No-op: return data as-is since no encryption
        return data

    async def decrypt(self, encrypted_data: str) -> str:
        """
        No-op: return data as-is.

        Args:
            encrypted_data: Encrypted data (passed through unchanged)

        Returns:
            Data unchanged (no decryption)
        """
        logger.debug("NoCrypto.decrypt called (no-op)")
        # No-op: return data as-is since no decryption
        return encrypted_data

    async def health_check(self) -> dict[str, Any]:
        """
        Health check for the provider.

        Returns:
            Health status information
        """
        return {
            "provider_type": self.provider_type,
            "enabled": self.enabled,
            "healthy": True,
            "message": "No crypto provider (no encryption)",
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get provider statistics.

        Returns:
            Statistics (always empty for no-op provider)
        """
        return {
            "provider_type": self.provider_type,
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_response_time_ms": 0.0,
            "error_rate": 0.0,
        }

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"NoCrypto(provider_type={self.provider_type}, enabled={self.enabled})"

    def __repr__(self) -> str:
        """Detailed string representation of the provider."""
        return f"NoCrypto(provider_type='{self.provider_type}', enabled={self.enabled})"
