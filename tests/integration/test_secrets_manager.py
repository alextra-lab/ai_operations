"""
Integration tests for SecretsManager service.

Tests secret storage, retrieval, rotation, and deletion with real database operations.

P5-A20: Migrated to async database patterns (ADR-022).
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import Tool
from src.orchestrator.app.services.secrets_manager import SecretsManager


@pytest_asyncio.fixture
async def test_tool(db_session: AsyncSession) -> Tool:
    """Create a test tool for use in secrets tests."""
    tool = Tool(
        tool_id=f"test_tool_{uuid4().hex[:8]}",
        name="Test Tool",
        category="database",
        tool_purpose="retrieval",
        service_location="retrieval_service",
        mcp_server_type="stdio",
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest_asyncio.fixture
async def secrets_manager(db_session: AsyncSession, monkeypatch):
    """Create SecretsManager instance for testing."""
    # Set encryption key for tests
    test_key = "test_key_minimum_32_characters_for_aes256_encryption"
    monkeypatch.setenv("TOOL_SECRETS_KEY", test_key)
    return SecretsManager(db_session, encryption_key_id="test")


class TestSecretsManagerIntegration:
    """Integration tests for SecretsManager with real database."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret(self, secrets_manager, test_tool):
        """Test that secret can be stored and retrieved."""
        # Store secret
        secret = await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="elasticsearch_api_key",
            secret_type="api_key",
            secret_value="super_secret_key_12345",
        )

        assert secret.id is not None
        assert secret.secret_name == "elasticsearch_api_key"
        assert secret.secret_type == "api_key"
        assert secret.tool_id == test_tool.id

        # Retrieve secret
        retrieved = await secrets_manager.retrieve_secret("elasticsearch_api_key")

        assert retrieved == "super_secret_key_12345"

        # Clean up
        await secrets_manager.delete_secret("elasticsearch_api_key")

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_secret(self, secrets_manager):
        """Test that retrieving nonexistent secret returns None."""
        result = await secrets_manager.retrieve_secret("nonexistent_secret")
        assert result is None

    @pytest.mark.asyncio
    async def test_secret_rotation(self, secrets_manager, test_tool):
        """Test that secret can be rotated."""
        # Store initial secret
        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="rotatable_api_key",
            secret_type="api_key",
            secret_value="old_key",
        )

        # Verify initial value
        retrieved = await secrets_manager.retrieve_secret("rotatable_api_key")
        assert retrieved == "old_key"

        # Rotate secret
        success = await secrets_manager.rotate_secret("rotatable_api_key", "new_key")
        assert success

        # Verify new value
        retrieved = await secrets_manager.retrieve_secret("rotatable_api_key")
        assert retrieved == "new_key"

        # Clean up
        await secrets_manager.delete_secret("rotatable_api_key")

    @pytest.mark.asyncio
    async def test_secret_expiration(self, secrets_manager, test_tool):
        """Test that expired secrets cannot be retrieved."""
        # Store secret with expiration in the past
        expired_time = datetime.now(tz=UTC) - timedelta(days=1)

        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="expired_api_key",
            secret_type="api_key",
            secret_value="secret_value",
            expires_at=expired_time,
        )

        # Try to retrieve expired secret
        retrieved = await secrets_manager.retrieve_secret("expired_api_key")
        assert retrieved is None

        # Clean up
        await secrets_manager.delete_secret("expired_api_key")

    @pytest.mark.asyncio
    async def test_secret_deletion(self, secrets_manager, test_tool):
        """Test that secret can be deleted (deactivated)."""
        # Store secret
        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="deletable_api_key",
            secret_type="api_key",
            secret_value="secret_value",
        )

        # Verify it exists
        retrieved = await secrets_manager.retrieve_secret("deletable_api_key")
        assert retrieved == "secret_value"

        # Delete (deactivate) secret
        deleted = await secrets_manager.delete_secret("deletable_api_key")
        assert deleted

        # Verify it cannot be retrieved
        retrieved = await secrets_manager.retrieve_secret("deletable_api_key")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_secret_access_tracking(
        self, secrets_manager, test_tool, db_session: AsyncSession
    ):
        """Test that secret access is tracked."""
        # Store secret
        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="tracked_api_key",
            secret_type="api_key",
            secret_value="secret_value",
        )

        # Retrieve secret multiple times
        for _ in range(3):
            await secrets_manager.retrieve_secret("tracked_api_key")

        # Verify access count was updated
        from sqlalchemy import text

        result = await db_session.execute(
            text(
                "SELECT access_count, last_accessed_at FROM tool_secrets WHERE secret_name = :name"
            ),
            {"name": "tracked_api_key"},
        )
        row = result.fetchone()

        assert row is not None
        assert row.access_count == 3
        assert row.last_accessed_at is not None

        # Clean up
        await secrets_manager.delete_secret("tracked_api_key")

    @pytest.mark.asyncio
    async def test_secret_unique_constraint(
        self, secrets_manager, test_tool, db_session: AsyncSession
    ):
        """Test that secret names must be unique."""
        # Store first secret
        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="unique_test_key",
            secret_type="api_key",
            secret_value="first_value",
        )

        # Try to store second secret with same name (different tool)
        another_tool = Tool(
            tool_id=f"another_tool_{uuid4().hex[:8]}",
            name="Another Tool",
            category="database",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="stdio",
        )
        db_session.add(another_tool)
        await db_session.commit()

        # This should fail due to unique constraint on secret_name
        with pytest.raises(Exception):  # Should raise IntegrityError
            await secrets_manager.store_secret(
                tool_id=another_tool.id,
                secret_name="unique_test_key",  # Same name
                secret_type="api_key",
                secret_value="second_value",
            )

        # Clean up
        await secrets_manager.delete_secret("unique_test_key")
        # Note: another_tool will be cleaned up by fixture rollback

    @pytest.mark.asyncio
    async def test_rotate_inactive_secret_returns_false(self, secrets_manager, test_tool):
        """Test that rotating inactive secret returns False."""
        # Store and delete secret
        await secrets_manager.store_secret(
            tool_id=test_tool.id,
            secret_name="inactive_secret",
            secret_type="api_key",
            secret_value="old_value",
        )

        await secrets_manager.delete_secret("inactive_secret")

        # Try to rotate inactive secret
        success = await secrets_manager.rotate_secret("inactive_secret", "new_value")
        assert success is False

    @pytest.mark.asyncio
    async def test_missing_encryption_key_raises_error(self, db_session: AsyncSession):
        """Test that missing encryption key raises ValueError."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="TOOL_SECRETS_KEY environment variable not set"),
        ):
            manager = SecretsManager(db_session)
            manager._get_encryption_key()
