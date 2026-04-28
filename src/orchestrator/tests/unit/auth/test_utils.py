"""
Unit tests for authentication utilities.

Tests async versions of auth functions (ADR-022 - async only).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from app.auth import utils

# =============================================================================
# PASSWORD UTILITIES (sync - no DB operations)
# =============================================================================


def test_get_password_hash_and_verify():
    """Test password hashing and verification."""
    pw = "secret"
    hashed = utils.get_password_hash(pw)
    assert utils.verify_password(pw, hashed)
    assert not utils.verify_password("wrong", hashed)


# =============================================================================
# ASYNC USER FUNCTIONS (ADR-022)
# =============================================================================


@pytest.mark.asyncio
async def test_get_user_found():
    """Test async get_user returns user when found."""
    db = AsyncMock()
    user = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.get_user(db, "alice")

    assert result is user


@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test async get_user returns None when not found."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.get_user(db, "bob")

    assert result is None


@pytest.mark.asyncio
@patch("app.auth.utils.verify_password", return_value=True)
async def test_authenticate_user_success(mock_verify):
    """Test async authenticate_user success."""
    db = AsyncMock()
    user = MagicMock()
    user.hashed_password = "hashed"
    user.id = "user-uuid-123"
    user.role = "user"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.authenticate_user(db, "alice", "pw")

    assert result is user


@pytest.mark.asyncio
@patch("app.auth.utils.verify_password", return_value=False)
async def test_authenticate_user_bad_password(mock_verify):
    """Test async authenticate_user with bad password."""
    db = AsyncMock()
    user = MagicMock()
    user.hashed_password = "hashed"
    user.id = "user-uuid-123"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.authenticate_user(db, "alice", "bad")

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Test async authenticate_user when user not found."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.authenticate_user(db, "bob", "pw")

    assert result is None


# Helper for refresh token tests
def make_refresh_token(revoked=False, expired=False):
    """Create a mock refresh token for testing."""
    rt = MagicMock()
    rt.revoked = revoked
    rt.user = MagicMock()
    rt.user_id = 1
    if expired:
        rt.expires_at = datetime.now(UTC) - timedelta(days=1)
    else:
        rt.expires_at = datetime.now(UTC) + timedelta(days=1)
    return rt


# =============================================================================
# ASYNC REFRESH TOKEN FUNCTIONS (ADR-022)
# =============================================================================


@pytest.mark.asyncio
async def test_store_refresh_token():
    """Test async store_refresh_token."""
    db = AsyncMock()
    user_id = "user-uuid-123"
    token = "token"
    expires = datetime.now(UTC) + timedelta(days=1)
    refresh_token = MagicMock()
    refresh_token.id = "token-uuid-123"

    with patch("app.auth.utils.RefreshToken", return_value=refresh_token):
        result = await utils.store_refresh_token(db, user_id, token, expires)

    db.add.assert_called_once_with(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    assert result is refresh_token


@pytest.mark.asyncio
async def test_get_refresh_token_found():
    """Test async get_refresh_token when found."""
    db = AsyncMock()
    rt = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = rt
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.get_refresh_token(db, "token")

    assert result is rt


@pytest.mark.asyncio
async def test_get_refresh_token_not_found():
    """Test async get_refresh_token when not found."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await utils.get_refresh_token(db, "token")

    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_valid():
    """Test async validate_refresh_token with valid token."""
    db = AsyncMock()
    rt = make_refresh_token()
    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.validate_refresh_token(db, "token")
    assert result is rt.user


@pytest.mark.asyncio
async def test_validate_refresh_token_not_found():
    """Test async validate_refresh_token when not found."""
    db = AsyncMock()
    with patch("app.auth.utils.get_refresh_token", return_value=None):
        result = await utils.validate_refresh_token(db, "token")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_revoked():
    """Test async validate_refresh_token when revoked."""
    db = AsyncMock()
    rt = make_refresh_token(revoked=True)
    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.validate_refresh_token(db, "token")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_expired():
    """Test async validate_refresh_token when expired."""
    db = AsyncMock()
    rt = make_refresh_token(expired=True)
    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.validate_refresh_token(db, "token")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_refresh_token_success():
    """Test async revoke_refresh_token success."""
    db = AsyncMock()
    rt = make_refresh_token()
    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.revoke_refresh_token(db, "token")
    assert result is True
    await db.commit()
    assert rt.revoked is True


@pytest.mark.asyncio
async def test_revoke_refresh_token_not_found():
    """Test async revoke_refresh_token when not found."""
    db = AsyncMock()
    with patch("app.auth.utils.get_refresh_token", return_value=None):
        result = await utils.revoke_refresh_token(db, "token")
    assert result is False


@pytest.mark.asyncio
async def test_revoke_refresh_token_already_revoked():
    """Test async revoke_refresh_token when already revoked."""
    db = AsyncMock()
    rt = make_refresh_token(revoked=True)
    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.revoke_refresh_token(db, "token")
    assert result is False


# =============================================================================
# UUID HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_store_refresh_token_with_uuid_string():
    """Test async store_refresh_token with UUID string."""
    db = AsyncMock()
    user_id = "550e8400-e29b-41d4-a716-446655440000"  # UUID string
    token = "token"
    expires = datetime.now(UTC) + timedelta(days=1)
    refresh_token = MagicMock()
    refresh_token.id = "token-uuid-123"

    with (
        patch("app.auth.utils.RefreshToken", return_value=refresh_token),
        patch("uuid.UUID") as mock_uuid,
    ):
        mock_uuid.return_value = user_id
        result = await utils.store_refresh_token(db, user_id, token, expires)

    db.add.assert_called_once_with(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    assert result is refresh_token


@pytest.mark.asyncio
async def test_store_refresh_token_with_uuid_object():
    """Test async store_refresh_token with UUID instance (e.g. user.id)."""
    db = AsyncMock()
    user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    token = "token"
    expires = datetime.now(UTC) + timedelta(days=1)
    refresh_token = MagicMock()
    refresh_token.id = "token-uuid-123"

    with patch("app.auth.utils.RefreshToken", return_value=refresh_token):
        result = await utils.store_refresh_token(db, user_id, token, expires)

    db.add.assert_called_once_with(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    assert result is refresh_token


@pytest.mark.asyncio
async def test_store_refresh_token_with_invalid_uuid_string():
    """Test async store_refresh_token with invalid UUID string raises."""
    db = AsyncMock()
    user_id = "invalid-uuid"  # Invalid UUID string
    token = "token"
    expires = datetime.now(UTC) + timedelta(days=1)

    with pytest.raises(ValueError, match="Invalid UUID"):
        await utils.store_refresh_token(db, user_id, token, expires)

    db.add.assert_not_called()


# =============================================================================
# ENHANCED LOGGING TESTS
# =============================================================================


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_authenticate_user_enhanced_logging(mock_logger):
    """Test that authenticate_user logs with enhanced context."""
    db = AsyncMock()
    user = MagicMock()
    user.hashed_password = "hashed"
    user.id = "user-uuid-123"
    user.role = "admin"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.auth.utils.verify_password", return_value=True):
        result = await utils.authenticate_user(db, "alice", "pw")

    assert result is user

    # Check that success logging was called with enhanced context
    mock_logger.info.assert_called()
    success_call = None
    for call in mock_logger.info.call_args_list:
        if "User authenticated successfully" in str(call):
            success_call = call
            break

    assert success_call is not None
    call_kwargs = success_call[1]["extra"]
    assert call_kwargs["username"] == "alice"
    assert call_kwargs["user_id"] == "user-uuid-123"
    assert call_kwargs["role"] == "admin"
    assert call_kwargs["event"] == "auth_success"


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_authenticate_user_failure_logging(mock_logger):
    """Test that authenticate_user logs failures with enhanced context."""
    db = AsyncMock()
    user = MagicMock()
    user.hashed_password = "hashed"
    user.id = "user-uuid-123"
    user.role = "user"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.auth.utils.verify_password", return_value=False):
        result = await utils.authenticate_user(db, "alice", "bad_password")

    assert result is None

    # Check that failure logging was called with enhanced context
    mock_logger.info.assert_called()
    failure_call = None
    for call in mock_logger.info.call_args_list:
        if "Authentication failed: invalid password" in str(call):
            failure_call = call
            break

    assert failure_call is not None
    call_kwargs = failure_call[1]["extra"]
    assert call_kwargs["username"] == "alice"
    assert call_kwargs["user_id"] == "user-uuid-123"
    assert call_kwargs["event"] == "auth_failure"
    assert call_kwargs["reason"] == "invalid_password"


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_validate_refresh_token_enhanced_logging(mock_logger):
    """Test that validate_refresh_token logs with enhanced context."""
    db = AsyncMock()
    rt = make_refresh_token()
    rt.user_id = "user-uuid-123"

    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.validate_refresh_token(db, "token")

    assert result is rt.user

    # Check that success logging was called with enhanced context
    mock_logger.info.assert_called()
    success_call = None
    for call in mock_logger.info.call_args_list:
        if "Refresh token validated successfully" in str(call):
            success_call = call
            break

    assert success_call is not None
    call_kwargs = success_call[1]["extra"]
    assert call_kwargs["token"] == "token"
    assert call_kwargs["user_id"] == "user-uuid-123"
    assert call_kwargs["event"] == "token_validation_success"


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_validate_refresh_token_expired_logging(mock_logger):
    """Test that validate_refresh_token logs expired tokens with enhanced context."""
    db = AsyncMock()
    rt = make_refresh_token(expired=True)
    rt.user_id = "user-uuid-123"
    rt.expires_at = datetime.now(UTC) - timedelta(days=1)

    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.validate_refresh_token(db, "token")

    assert result is None

    # Check that failure logging was called with enhanced context
    mock_logger.info.assert_called()
    failure_call = None
    for call in mock_logger.info.call_args_list:
        if "Refresh token validation failed: expired" in str(call):
            failure_call = call
            break

    assert failure_call is not None
    call_kwargs = failure_call[1]["extra"]
    assert call_kwargs["token"] == "token"
    assert call_kwargs["user_id"] == "user-uuid-123"
    assert call_kwargs["event"] == "token_validation_failure"
    assert call_kwargs["reason"] == "token_expired"
    assert "expires_at" in call_kwargs


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_revoke_refresh_token_enhanced_logging(mock_logger):
    """Test that revoke_refresh_token logs with enhanced context."""
    db = AsyncMock()
    rt = make_refresh_token()
    rt.user_id = "user-uuid-123"

    with patch("app.auth.utils.get_refresh_token", return_value=rt):
        result = await utils.revoke_refresh_token(db, "token")

    assert result is True
    await db.commit()
    assert rt.revoked is True

    # Check that success logging was called with enhanced context
    mock_logger.info.assert_called()
    success_call = None
    for call in mock_logger.info.call_args_list:
        if "Refresh token revoked successfully" in str(call):
            success_call = call
            break

    assert success_call is not None
    call_kwargs = success_call[1]["extra"]
    assert call_kwargs["token"] == "token"
    assert call_kwargs["user_id"] == "user-uuid-123"
    assert call_kwargs["event"] == "token_revoke_success"
    assert "revoked_at" in call_kwargs


@patch("app.auth.utils.logger")
@pytest.mark.asyncio
async def test_revoke_refresh_token_not_found_logging(mock_logger):
    """Test that revoke_refresh_token logs not found tokens with enhanced context."""
    db = AsyncMock()

    with patch("app.auth.utils.get_refresh_token", return_value=None):
        result = await utils.revoke_refresh_token(db, "token")

    assert result is False

    # Check that failure logging was called with enhanced context
    mock_logger.info.assert_called()
    failure_call = None
    for call in mock_logger.info.call_args_list:
        if "Revoke refresh token failed: not found" in str(call):
            failure_call = call
            break

    assert failure_call is not None
    call_kwargs = failure_call[1]["extra"]
    assert call_kwargs["token"] == "token"
    assert call_kwargs["event"] == "token_revoke_failure"
    assert call_kwargs["reason"] == "token_not_found"
