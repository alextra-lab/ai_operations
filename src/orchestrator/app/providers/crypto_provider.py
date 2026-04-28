"""
Crypto provider interfaces and implementations.

Defines the CryptoProvider protocol and provides no-op implementation
for stateless v1 architecture (ADR-033).
"""

from typing import Protocol


class CryptoProvider(Protocol):
    """
    Protocol for cryptographic operations.

    In stateless v1, encryption is not required (no server-side data storage).
    In future stateful v2+, this enables KmsCrypto provider with HSM/KMS integration.
    """

    async def encrypt(self, data: str) -> str:
        """
        Encrypt data.

        Args:
            data: Plaintext data

        Returns:
            Encrypted data
        """
        ...

    async def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data.

        Args:
            encrypted_data: Encrypted data

        Returns:
            Plaintext data
        """
        ...


class NoCrypto:
    """
    No-op crypto provider for stateless v1.

    This implementation satisfies the CryptoProvider protocol but does
    not perform any encryption. Since no sensitive conversation data is
    stored server-side, encryption is not required.

    ADR-033: Provider Interfaces (Disabled for v1)
    ADR-030: No server-side conversation storage = no encryption needed
    """

    async def encrypt(self, data: str) -> str:
        """
        No-op: return data as-is.

        Encryption is not required in stateless architecture because
        no sensitive conversation data is stored server-side.
        """
        return data

    async def decrypt(self, encrypted_data: str) -> str:
        """
        No-op: return data as-is.

        Decryption is not applicable in stateless v1.
        """
        return encrypted_data
