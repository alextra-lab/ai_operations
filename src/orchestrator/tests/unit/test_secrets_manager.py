"""
Unit tests for SecretsManager service.

Tests secret storage, retrieval, rotation, and deletion operations.
All database operations are mocked - no real database interaction.
"""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import ToolSecret
from app.services.secrets_manager import SecretsManager
from sqlalchemy.engine import Result


@pytest.fixture
def mock_db_session():
    """Mock database session with all necessary methods."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    return session


@pytest.fixture
def mock_tool_id():
    """Sample tool ID for testing."""
    return uuid4()


@pytest.fixture
def sample_tool_secret(mock_tool_id):
    """Sample ToolSecret object for testing."""
    now = datetime.now(tz=UTC)
    return ToolSecret(
        id=uuid4(),
        tool_id=mock_tool_id,
        secret_name="test_api_key",
        secret_type="api_key",
        encrypted_value=b"encrypted_data",
        encryption_key_id="default",
        is_active=True,
        expires_at=None,
        created_at=now,
        created_by=None,
        last_accessed_at=None,
        access_count=0,
    )


@pytest.fixture(autouse=True)
def set_env_var():
    """Set TOOL_SECRETS_KEY environment variable for all tests."""
    with patch.dict(
        os.environ, {"TOOL_SECRETS_KEY": "test_key_minimum_32_characters_long"}, clear=False
    ):
        yield


@pytest.fixture
def secrets_manager(mock_db_session):
    """Create SecretsManager instance with mocked dependencies."""
    return SecretsManager(mock_db_session, encryption_key_id="default")


class TestSecretsManager:
    """Test SecretsManager service operations."""

    def test_init_creates_pgcrypto_extension(self, mock_db_session):
        """Test that initialization ensures pgcrypto is installed."""
        # Mock successful extension creation
        mock_result = MagicMock()
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit.return_value = None

        SecretsManager(mock_db_session)

        # Verify extension check was attempted
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called

    def test_get_encryption_key_from_environment(self, mock_db_session):
        """Test that encryption key is retrieved from environment."""
        test_key = "test_encryption_key_minimum_32_characters_long"
        with patch.dict(os.environ, {"TOOL_SECRETS_KEY": test_key}, clear=False):
            manager = SecretsManager(mock_db_session)
            key = manager._get_encryption_key()
            assert key == test_key

    def test_get_encryption_key_missing_raises_error(self, mock_db_session):
        """Test that missing encryption key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            manager = SecretsManager(mock_db_session)
            with pytest.raises(ValueError, match="TOOL_SECRETS_KEY environment variable not set"):
                manager._get_encryption_key()

    def test_store_secret_encrypts_value(self, secrets_manager, mock_tool_id, mock_db_session):
        """Test that store_secret encrypts the secret value."""
        # Mock the INSERT query result
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_row.tool_id = mock_tool_id
        mock_row.secret_name = "test_api_key"
        mock_row.secret_type = "api_key"
        mock_row.is_active = True
        mock_row.expires_at = None
        mock_row.created_at = datetime.now(tz=UTC)
        mock_row.created_by = None
        mock_row.encryption_key_id = "default"

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        # Store secret
        secret = secrets_manager.store_secret(
            tool_id=mock_tool_id,
            secret_name="test_api_key",
            secret_type="api_key",
            secret_value="super_secret_key_12345",
        )

        # Verify encryption was called
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called
        assert secret.secret_name == "test_api_key"
        assert secret.secret_type == "api_key"

    def test_store_secret_with_expiration(self, secrets_manager, mock_tool_id, mock_db_session):
        """Test storing secret with expiration date."""
        expires_at = datetime.now(tz=UTC).replace(year=2026)

        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_row.tool_id = mock_tool_id
        mock_row.secret_name = "expiring_key"
        mock_row.secret_type = "api_key"
        mock_row.is_active = True
        mock_row.expires_at = expires_at
        mock_row.created_at = datetime.now(tz=UTC)
        mock_row.created_by = None
        mock_row.encryption_key_id = "default"

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        secret = secrets_manager.store_secret(
            tool_id=mock_tool_id,
            secret_name="expiring_key",
            secret_type="api_key",
            secret_value="secret_value",
            expires_at=expires_at,
        )

        assert secret.expires_at == expires_at
        assert mock_db_session.commit.called

    def test_retrieve_secret_decrypts_value(self, secrets_manager, mock_db_session):
        """Test that retrieve_secret decrypts the secret value."""
        # Mock the SELECT query result
        mock_row = MagicMock()
        mock_row.decrypted_value = b"super_secret_key_12345"
        mock_row.is_active = True
        mock_row.expires_at = None

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        # Retrieve secret
        retrieved = secrets_manager.retrieve_secret("test_api_key")

        # Verify decryption was called
        assert mock_db_session.execute.called
        assert retrieved == "super_secret_key_12345"

    def test_retrieve_secret_not_found_returns_none(self, secrets_manager, mock_db_session):
        """Test that retrieving nonexistent secret returns None."""
        # Mock no result
        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        retrieved = secrets_manager.retrieve_secret("nonexistent_secret")

        assert retrieved is None

    def test_retrieve_secret_inactive_returns_none(self, secrets_manager, mock_db_session):
        """Test that retrieving inactive secret returns None."""
        mock_row = MagicMock()
        mock_row.is_active = False
        mock_row.expires_at = None

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        retrieved = secrets_manager.retrieve_secret("inactive_secret")

        assert retrieved is None

    def test_retrieve_secret_expired_returns_none(self, secrets_manager, mock_db_session):
        """Test that retrieving expired secret returns None."""
        expired_time = datetime.now(tz=UTC).replace(year=2020)

        mock_row = MagicMock()
        mock_row.decrypted_value = b"secret_value"
        mock_row.is_active = True
        mock_row.expires_at = expired_time

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        retrieved = secrets_manager.retrieve_secret("expired_secret")

        assert retrieved is None

    def test_retrieve_secret_updates_access_tracking(self, secrets_manager, mock_db_session):
        """Test that retrieving secret updates access tracking."""
        mock_row = MagicMock()
        mock_row.decrypted_value = b"secret_value"
        mock_row.is_active = True
        mock_row.expires_at = None

        # First call for pgcrypto extension check (in __init__),
        # second call for SELECT, third call for UPDATE
        MagicMock(spec=Result)
        mock_result_select = MagicMock(spec=Result)
        mock_result_select.fetchone.return_value = mock_row
        mock_result_update = MagicMock(spec=Result)

        # Reset mock to start fresh call count
        mock_db_session.execute.reset_mock()
        mock_db_session.execute.side_effect = [mock_result_select, mock_result_update]

        secrets_manager.retrieve_secret("test_api_key", update_access_tracking=True)

        # Verify UPDATE query was executed (SELECT + UPDATE = 2 calls after reset)
        assert mock_db_session.execute.call_count == 2
        assert mock_db_session.commit.called

    def test_delete_secret_deactivates(self, secrets_manager, mock_db_session):
        """Test that delete_secret deactivates the secret."""
        mock_row = MagicMock()
        mock_row.id = uuid4()

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        deleted = secrets_manager.delete_secret("test_api_key")

        assert deleted is True
        assert mock_db_session.commit.called

    def test_delete_secret_nonexistent_returns_false(self, secrets_manager, mock_db_session):
        """Test that deleting nonexistent secret returns False."""
        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        deleted = secrets_manager.delete_secret("nonexistent_secret")

        assert deleted is False

    def test_rotate_secret_updates_value(self, secrets_manager, mock_db_session):
        """Test that rotate_secret updates the encrypted value."""
        mock_row = MagicMock()
        mock_row.id = uuid4()

        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        rotated = secrets_manager.rotate_secret("test_api_key", "new_secret_value")

        assert rotated is True
        assert mock_db_session.commit.called

    def test_rotate_secret_nonexistent_returns_false(self, secrets_manager, mock_db_session):
        """Test that rotating nonexistent secret returns False."""
        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        rotated = secrets_manager.rotate_secret("nonexistent_secret", "new_value")

        assert rotated is False

    def test_rotate_secret_inactive_returns_false(self, secrets_manager, mock_db_session):
        """Test that rotating inactive secret returns False."""
        # Mock no result (inactive secrets are filtered in WHERE clause)
        mock_result = MagicMock(spec=Result)
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        rotated = secrets_manager.rotate_secret("inactive_secret", "new_value")

        assert rotated is False
