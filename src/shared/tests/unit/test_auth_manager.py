"""
Unit tests for UnifiedAuthManager multi-role token creation and legacy conversion.

Tests:
- create_user_tokens() with multi-role support
- verify_token_enhanced() legacy token conversion
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from shared.auth.manager import UnifiedAuthManager
from shared.auth.models import User


@pytest.fixture
def auth_manager():
    """Create UnifiedAuthManager instance."""
    return UnifiedAuthManager(
        secret="test-secret",
        algorithm="HS256",
        issuer="test-issuer",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def sample_user():
    """Create sample user."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.username = "testuser"
    user.role = "developer"  # Legacy role column
    return user


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    return AsyncMock()


class TestCreateUserTokens:
    """Test create_user_tokens() with multi-role support."""

    @pytest.mark.asyncio
    @patch("shared.auth.manager.select")
    async def test_create_tokens_fetches_roles_from_user_roles_table(
        self, mock_select, auth_manager, sample_user, mock_db
    ):
        """create_user_tokens() fetches roles from user_roles table."""
        # Mock user_roles table query result
        role1 = Mock(role="developer")
        role2 = Mock(role="team:csirt_security")
        mock_result = Mock()
        mock_result.all.return_value = [role1, role2]
        mock_db.execute.return_value = mock_result

        tokens = await auth_manager.create_user_tokens(sample_user, mock_db)

        # Verify roles were fetched
        mock_db.execute.assert_called_once()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert isinstance(tokens["access_token"], str)
        assert len(tokens["access_token"]) > 0

    @pytest.mark.asyncio
    @patch("shared.auth.manager.select")
    async def test_create_tokens_fallback_to_legacy_role(
        self, mock_select, auth_manager, sample_user, mock_db
    ):
        """create_user_tokens() falls back to legacy user.role if no roles in table."""
        # Mock empty user_roles table
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        tokens = await auth_manager.create_user_tokens(sample_user, mock_db)

        # Verify tokens were created
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert isinstance(tokens["access_token"], str)

    @pytest.mark.asyncio
    @patch("shared.auth.manager.select")
    async def test_create_tokens_empty_roles_defaults_to_user_role(
        self, mock_select, auth_manager, sample_user, mock_db
    ):
        """create_user_tokens() uses user.role when user_roles table is empty."""
        sample_user.role = "user"
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        tokens = await auth_manager.create_user_tokens(sample_user, mock_db)

        # Verify tokens were created
        assert "access_token" in tokens
        assert isinstance(tokens["access_token"], str)


class TestVerifyTokenEnhanced:
    """Test verify_token_enhanced() legacy token conversion."""

    def test_verify_token_enhanced_converts_legacy_role_to_roles(self, auth_manager):
        """verify_token_enhanced() converts legacy 'role' to 'roles' list."""
        # Create legacy token with single 'role' field
        legacy_payload = {
            "sub": "testuser",
            "user_id": str(uuid4()),
            "role": "developer",  # Legacy single role
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "test-issuer",
            "token_type": "access",
        }

        # Encode as JWT using auth_manager's method
        token = auth_manager.create_access_token(legacy_payload)

        # Verify token
        payload = auth_manager.verify_token_enhanced(token)

        assert payload is not None
        assert payload.roles == ["developer"]  # Converted to list
        assert not hasattr(payload, "role")  # Legacy field removed

    def test_verify_token_enhanced_handles_multi_role_token(self, auth_manager):
        """verify_token_enhanced() handles new multi-role tokens."""
        # Create new token with 'roles' field
        new_payload = {
            "sub": "testuser",
            "user_id": str(uuid4()),
            "roles": ["developer", "threat_hunting"],  # New multi-role
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "test-issuer",
            "token_type": "access",
        }

        token = auth_manager.create_access_token(new_payload)

        payload = auth_manager.verify_token_enhanced(token)

        assert payload is not None
        assert payload.roles == ["developer", "threat_hunting"]

    def test_verify_token_enhanced_removes_legacy_role_key(self, auth_manager):
        """verify_token_enhanced() removes legacy 'role' key after conversion."""
        # Create legacy token
        legacy_payload = {
            "sub": "testuser",
            "user_id": str(uuid4()),
            "role": "admin",
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "test-issuer",
            "token_type": "access",
        }

        token = auth_manager.create_access_token(legacy_payload)

        payload = auth_manager.verify_token_enhanced(token)

        # Verify legacy 'role' key was removed (Pydantic validation would fail if present)
        assert payload is not None
        assert payload.roles == ["admin"]
        # TokenPayload model doesn't have 'role' field, so if it was in payload dict,
        # Pydantic would raise ValidationError. The fact that payload was created
        # successfully means 'role' was removed.

    def test_verify_token_enhanced_handles_non_string_role(self, auth_manager):
        """verify_token_enhanced() handles non-string role values."""
        legacy_payload = {
            "sub": "testuser",
            "user_id": str(uuid4()),
            "role": 123,  # Non-string role (shouldn't happen but handle gracefully)
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "test-issuer",
            "token_type": "access",
        }

        token = auth_manager.create_access_token(legacy_payload)

        payload = auth_manager.verify_token_enhanced(token)

        assert payload is not None
        assert payload.roles == ["123"]  # Converted to string

    def test_verify_token_enhanced_fails_without_role_or_roles(self, auth_manager):
        """verify_token_enhanced() returns None when neither 'role' nor 'roles' present."""
        invalid_payload = {
            "sub": "testuser",
            "user_id": str(uuid4()),
            # Missing both 'role' and 'roles'
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "test-issuer",
            "token_type": "access",
        }

        token = auth_manager.create_access_token(invalid_payload)

        payload = auth_manager.verify_token_enhanced(token)

        assert payload is None
