"""
Secrets management for tool credentials.

Uses PostgreSQL pgcrypto for encryption with application-managed keys.
For production, consider external secrets manager (HashiCorp Vault, AWS Secrets Manager).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.secrets import resolve_secret
from shared.logging_utils.fastapi import configure_logging, mask_identifier

from ..db.models import ToolSecret

logger = configure_logging(service_name="secrets_manager")


class SecretsManager:
    """
    Manage encrypted secrets for tool authentication.

    Uses PostgreSQL pgcrypto extension for encryption.
    Encryption key derived from environment variable (TOOL_SECRETS_KEY).
    """

    def __init__(self, db: AsyncSession, encryption_key_id: str = "default"):
        """
        Initialize secrets manager.

        Args:
            db: Database session
            encryption_key_id: Identifier for encryption key (for key rotation)
        """
        self.db = db
        self.encryption_key_id = encryption_key_id
        self._pgcrypto_checked = False  # Lazy initialization flag

    async def _ensure_pgcrypto_installed(self) -> None:
        """Ensure pgcrypto extension is installed (lazy initialization)."""
        if self._pgcrypto_checked:
            return  # Already checked/installed

        try:
            await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await self.db.commit()
            self._pgcrypto_checked = True
            logger.debug("pgcrypto extension verified/installed")
        except Exception as e:
            logger.warning(f"pgcrypto extension check failed: {e}")
            # Don't raise - may already be installed, mark as checked to avoid retries
            self._pgcrypto_checked = True

    async def store_secret(
        self,
        tool_id: UUID,
        secret_name: str,
        secret_type: str,
        secret_value: str,
        expires_at: datetime | None = None,
        created_by: UUID | None = None,
    ) -> ToolSecret:
        """
        Store an encrypted secret for a tool.

        Args:
            tool_id: Tool UUID
            secret_name: Unique name for the secret
            secret_type: Type of secret (api_key, oauth_token, etc.)
            secret_value: Plain-text secret value (will be encrypted)
            expires_at: Optional expiration timestamp
            created_by: UUID of user creating the secret

        Returns:
            Created ToolSecret record (without decrypted value)
        """
        # Ensure pgcrypto extension is available
        await self._ensure_pgcrypto_installed()

        # Encrypt using pgcrypto
        encryption_key = self._get_encryption_key()

        query = text(
            """
            INSERT INTO tool_secrets (
                tool_id, secret_name, secret_type, encrypted_value,
                encryption_key_id, expires_at, is_active, created_by
            )
            VALUES (
                :tool_id, :secret_name, :secret_type,
                pgp_sym_encrypt(:secret_value, :encryption_key),
                :encryption_key_id, :expires_at, true, :created_by
            )
            RETURNING id, tool_id, secret_name, secret_type,
                      is_active, expires_at, created_at, created_by
        """
        )

        result = await self.db.execute(
            query,
            {
                "tool_id": str(tool_id),
                "secret_name": secret_name,
                "secret_type": secret_type,
                "secret_value": secret_value,
                "encryption_key": encryption_key,
                "encryption_key_id": self.encryption_key_id,
                "expires_at": expires_at,
                "created_by": str(created_by) if created_by else None,
            },
        )

        row = result.fetchone()
        if not row:
            await self.db.rollback()
            raise ValueError(f"Failed to store secret: {secret_name}")

        await self.db.commit()

        logger.info(
            "Stored encrypted secret",
            extra={"secret_ref": mask_identifier(secret_name), "tool_id": str(tool_id)},
        )

        # Create ToolSecret model instance from returned data
        return ToolSecret(
            id=row.id,
            tool_id=row.tool_id,
            secret_name=row.secret_name,
            secret_type=row.secret_type,
            is_active=row.is_active,
            expires_at=row.expires_at,
            created_at=row.created_at,
            created_by=row.created_by,
            encrypted_value=b"",  # Never expose encrypted value
            encryption_key_id=(
                row.encryption_key_id
                if hasattr(row, "encryption_key_id")
                else self.encryption_key_id
            ),
        )

    async def retrieve_secret(
        self, secret_name: str, update_access_tracking: bool = True
    ) -> str | None:
        """
        Retrieve and decrypt a secret value.

        Args:
            secret_name: Name of the secret
            update_access_tracking: Whether to update last_accessed_at

        Returns:
            Decrypted secret value, or None if not found/expired/inactive
        """
        # Ensure pgcrypto extension is available
        await self._ensure_pgcrypto_installed()

        encryption_key = self._get_encryption_key()

        query = text(
            """
            SELECT
                pgp_sym_decrypt(encrypted_value, :encryption_key) as decrypted_value,
                is_active,
                expires_at
            FROM tool_secrets
            WHERE secret_name = :secret_name
        """
        )

        result = await self.db.execute(
            query, {"secret_name": secret_name, "encryption_key": encryption_key}
        )

        row = result.fetchone()

        if not row:
            logger.warning(
                "Secret not found",
                extra={"secret_ref": mask_identifier(secret_name)},
            )
            return None

        if not row.is_active:
            logger.warning(
                "Secret inactive",
                extra={"secret_ref": mask_identifier(secret_name)},
            )
            return None

        if row.expires_at and row.expires_at < datetime.now(UTC):
            logger.warning(
                "Secret expired",
                extra={"secret_ref": mask_identifier(secret_name)},
            )
            return None

        # Update access tracking
        if update_access_tracking:
            await self._update_access_tracking(secret_name)

        logger.debug(
            "Retrieved secret",
            extra={"secret_ref": mask_identifier(secret_name)},
        )

        # Decrypted value comes as bytes, decode to string
        decrypted = row.decrypted_value
        if isinstance(decrypted, bytes):
            return decrypted.decode("utf-8")
        return str(decrypted) if decrypted is not None else None

    async def _update_access_tracking(self, secret_name: str) -> None:
        """Update last accessed timestamp and count."""
        update_query = text(
            """
            UPDATE tool_secrets
            SET
                last_accessed_at = NOW(),
                access_count = access_count + 1
            WHERE secret_name = :secret_name
        """
        )
        await self.db.execute(update_query, {"secret_name": secret_name})
        await self.db.commit()

    async def delete_secret(self, secret_name: str) -> bool:
        """
        Delete a secret (or mark as inactive).

        Args:
            secret_name: Name of the secret to delete

        Returns:
            True if deleted, False if not found
        """
        query = text(
            """
            UPDATE tool_secrets
            SET is_active = false, updated_at = NOW()
            WHERE secret_name = :secret_name
            RETURNING id
        """
        )

        result = await self.db.execute(query, {"secret_name": secret_name})
        deleted = result.fetchone() is not None
        await self.db.commit()

        if deleted:
            logger.info(
                "Deactivated secret",
                extra={"secret_ref": mask_identifier(secret_name)},
            )

        return deleted

    async def rotate_secret(self, secret_name: str, new_secret_value: str) -> bool:
        """
        Rotate a secret value (update with new encrypted value).

        Args:
            secret_name: Name of the secret to rotate
            new_secret_value: New plain-text secret value

        Returns:
            True if rotated successfully
        """
        # Ensure pgcrypto extension is available
        await self._ensure_pgcrypto_installed()

        encryption_key = self._get_encryption_key()

        query = text(
            """
            UPDATE tool_secrets
            SET
                encrypted_value = pgp_sym_encrypt(:new_value, :encryption_key),
                updated_at = NOW(),
                access_count = 0
            WHERE secret_name = :secret_name
            AND is_active = true
            RETURNING id
        """
        )

        result = await self.db.execute(
            query,
            {
                "secret_name": secret_name,
                "new_value": new_secret_value,
                "encryption_key": encryption_key,
            },
        )

        rotated = result.fetchone() is not None
        await self.db.commit()

        if rotated:
            logger.info(
                "Rotated secret",
                extra={"secret_ref": mask_identifier(secret_name)},
            )

        return rotated

    def _get_encryption_key(self) -> str:
        """
        Get encryption key from environment.

        In production, this should use a proper secrets management
        system like HashiCorp Vault or AWS Secrets Manager.

        Returns:
            Encryption key string

        Raises:
            ValueError: If TOOL_SECRETS_KEY environment variable is not set
        """
        key = resolve_secret("TOOL_SECRETS_KEY")
        if not key:
            raise ValueError(
                "TOOL_SECRETS_KEY environment variable not set. "
                "Required for tool secrets encryption."
            )
        if len(key) < 32:
            logger.warning(
                "TOOL_SECRETS_KEY is less than 32 characters. "
                "Recommend using at least 32 characters for AES-256 encryption."
            )
        return key
