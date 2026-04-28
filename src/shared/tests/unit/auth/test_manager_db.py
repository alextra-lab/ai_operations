"""
Unit tests for shared.auth.manager database operations.

Tests cover:
- User creation with database
- User authentication
- Refresh token operations
- Token validation
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from shared.auth.manager import UnifiedAuthManager
from shared.auth.models import RefreshToken, User, UserRole


@pytest.fixture
def manager():
    return UnifiedAuthManager(secret="testsecret")


@pytest.fixture
def db_session():
    """Create a mock async database session."""
    mock_session = MagicMock()

    # Configure the execute chain mock for async SQLAlchemy
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_scalars.first.return_value = None  # Default to None

    # Make execute an async method that returns the mock result
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Make commit and refresh async
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.add = MagicMock()

    # Store the mock result for easy access in tests
    mock_session._mock_result = mock_result
    mock_session._mock_scalars = mock_scalars
    return mock_session


@pytest.fixture
def user_data():
    return {
        "username": "testuser",
        "password": "password123",
        "full_name": "Test User",
        "email": "test@example.com",
        "role": UserRole.USER,
        "metadata": {},
    }


def make_user(user_data, **overrides):
    """Helper to create a User instance for testing."""
    data = {k: v for k, v in user_data.items() if k != "password"}
    data.update(
        {
            "id": uuid.uuid4(),
            "hashed_password": "hashed",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )
    data.update(overrides)
    return User(**data)


# =============================================================================
# CREATE USER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_create_user_duplicate_username(manager, db_session, user_data):
    """Test create_user raises error for duplicate username."""
    mock_user = make_user(user_data)
    db_session._mock_scalars.first.return_value = mock_user

    with pytest.raises(HTTPException) as excinfo:
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 400
    assert "Username already registered" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_create_user_duplicate_email(manager, db_session, user_data):
    """Test create_user raises error for duplicate email."""
    mock_user = make_user(user_data)
    # First call (username check) returns None, second (email check) returns user
    db_session._mock_scalars.first.side_effect = [None, mock_user]

    with pytest.raises(HTTPException) as excinfo:
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 400
    assert "Email already registered" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_create_user_invalid_role(manager, db_session, user_data):
    """Test create_user raises error for invalid role."""
    user_data["role"] = "notarole"
    db_session._mock_scalars.first.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 400
    assert "Invalid role" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_create_user_success(manager, db_session, user_data):
    """Test successful user creation."""
    db_session._mock_scalars.first.return_value = None

    with patch.object(manager, "get_password_hash", return_value="hashed"):
        result = await manager.create_user(db_session, **user_data)

    assert result is not None
    db_session.add.assert_called_once()
    db_session.commit.assert_awaited_once()
    db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_db_error(manager, db_session, user_data):
    """Test create_user handles database add error."""
    db_session._mock_scalars.first.return_value = None
    db_session.add.side_effect = Exception("db error")

    with (
        patch.object(manager, "get_password_hash", return_value="hashed"),
        pytest.raises(HTTPException) as excinfo,
    ):
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_create_user_db_commit_error(manager, db_session, user_data):
    """Test create_user handles database commit error."""
    db_session._mock_scalars.first.return_value = None
    db_session.commit.side_effect = Exception("db error")

    with (
        patch.object(manager, "get_password_hash", return_value="hashed"),
        pytest.raises(HTTPException) as excinfo,
    ):
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_create_user_db_refresh_error(manager, db_session, user_data):
    """Test create_user handles database refresh error."""
    db_session._mock_scalars.first.return_value = None
    db_session.refresh.side_effect = Exception("db error")

    with (
        patch.object(manager, "get_password_hash", return_value="hashed"),
        pytest.raises(HTTPException) as excinfo,
    ):
        await manager.create_user(db_session, **user_data)
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_create_user_db_commit_rollback(manager, db_session, user_data):
    """Test create_user rolls back on commit error."""
    db_session._mock_scalars.first.return_value = None
    db_session.commit.side_effect = Exception("db error")

    with (
        patch.object(manager, "get_password_hash", return_value="hashed"),
        patch("shared.auth.manager.logger.error") as mock_log,
        pytest.raises(HTTPException),
    ):
        await manager.create_user(db_session, **user_data)
    db_session.rollback.assert_awaited()
    assert mock_log.called


# =============================================================================
# AUTHENTICATE USER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_authenticate_user_success(manager, db_session, user_data):
    """Test successful user authentication."""
    user = make_user(user_data, hashed_password=manager.get_password_hash(user_data["password"]))
    db_session._mock_scalars.first.return_value = user

    result = await manager.authenticate_user(db_session, user.username, user_data["password"])
    assert result is user


@pytest.mark.asyncio
async def test_authenticate_user_not_found(manager, db_session, user_data):
    """Test authentication fails for non-existent user."""
    db_session._mock_scalars.first.return_value = None

    result = await manager.authenticate_user(
        db_session, user_data["username"], user_data["password"]
    )
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_inactive(manager, db_session, user_data):
    """Test authentication fails for inactive user."""
    user = make_user(
        user_data,
        hashed_password=manager.get_password_hash(user_data["password"]),
        is_active=False,
    )
    db_session._mock_scalars.first.return_value = user

    result = await manager.authenticate_user(db_session, user.username, user_data["password"])
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(manager, db_session, user_data):
    """Test authentication fails for wrong password."""
    user = make_user(user_data, hashed_password=manager.get_password_hash("wrongpass"))
    db_session._mock_scalars.first.return_value = user

    result = await manager.authenticate_user(db_session, user.username, user_data["password"])
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_db_error(manager, db_session, user_data):
    """Test authentication handles database error."""
    db_session.execute.side_effect = Exception("db error")

    result = await manager.authenticate_user(
        db_session, user_data["username"], user_data["password"]
    )
    assert result is None


# =============================================================================
# REFRESH TOKEN TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_store_refresh_token_success(manager, db_session):
    """Test successful refresh token storage."""
    token = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(days=1)

    result = await manager.store_refresh_token(db_session, uuid.uuid4(), token, expires_at)

    assert isinstance(result, RefreshToken)
    db_session.add.assert_called_once()
    db_session.commit.assert_awaited_once()
    db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_refresh_token_db_error(manager, db_session):
    """Test refresh token storage handles database error."""
    db_session.add.side_effect = Exception("db error")

    with pytest.raises(Exception):
        await manager.store_refresh_token(db_session, uuid.uuid4(), "token", datetime.now(UTC))


@pytest.mark.asyncio
async def test_store_refresh_token_commit_error(manager, db_session):
    """Test refresh token storage handles commit error."""
    db_session.commit.side_effect = Exception("db error")

    with pytest.raises(Exception):
        await manager.store_refresh_token(db_session, uuid.uuid4(), "token", datetime.now(UTC))


@pytest.mark.asyncio
async def test_store_refresh_token_refresh_error(manager, db_session):
    """Test refresh token storage handles refresh error."""
    db_session.refresh.side_effect = Exception("db error")

    with pytest.raises(Exception):
        await manager.store_refresh_token(db_session, uuid.uuid4(), "token", datetime.now(UTC))


@pytest.mark.asyncio
async def test_validate_refresh_token_not_found(manager, db_session):
    """Test validation fails for non-existent token."""
    db_session._mock_scalars.first.return_value = None

    result = await manager.validate_refresh_token(db_session, "sometoken")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_revoked(manager, db_session):
    """Test validation fails for revoked token."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=True,
    )
    db_session._mock_scalars.first.return_value = token

    result = await manager.validate_refresh_token(db_session, "t")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_expired(manager, db_session):
    """Test validation fails for expired token."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) - timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=False,
    )
    db_session._mock_scalars.first.return_value = token

    result = await manager.validate_refresh_token(db_session, "t")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_user_inactive(manager, db_session):
    """Test validation fails for inactive user."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=False,
    )
    user = User(
        id=token.user_id,
        username="u",
        full_name="f",
        email="e",
        hashed_password="h",
        role=UserRole.USER,
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_active=False,
    )
    # First call returns token, second returns user
    db_session._mock_scalars.first.side_effect = [token, user]

    result = await manager.validate_refresh_token(db_session, "t")
    assert result is None


@pytest.mark.asyncio
async def test_validate_refresh_token_success(manager, db_session):
    """Test successful token validation."""
    user_id = uuid.uuid4()
    token = RefreshToken(
        token="t",
        user_id=user_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=False,
    )
    user = User(
        id=user_id,
        username="u",
        full_name="f",
        email="e",
        hashed_password="h",
        role=UserRole.USER,
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_active=True,
    )
    # First call returns token, second returns user
    db_session._mock_scalars.first.side_effect = [token, user]

    result = await manager.validate_refresh_token(db_session, "t")
    assert result is user


@pytest.mark.asyncio
async def test_validate_refresh_token_exception(manager, db_session):
    """Test validation handles database exception."""
    db_session.execute.side_effect = Exception("db error")

    result = await manager.validate_refresh_token(db_session, "token")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_refresh_token_not_found(manager, db_session):
    """Test revocation fails for non-existent token."""
    db_session._mock_scalars.first.return_value = None

    result = await manager.revoke_refresh_token(db_session, "t")
    assert result is False


@pytest.mark.asyncio
async def test_revoke_refresh_token_already_revoked(manager, db_session):
    """Test revocation fails for already revoked token."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=True,
    )
    db_session._mock_scalars.first.return_value = token

    result = await manager.revoke_refresh_token(db_session, "t")
    assert result is False


@pytest.mark.asyncio
async def test_revoke_refresh_token_success(manager, db_session):
    """Test successful token revocation."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=False,
    )
    db_session._mock_scalars.first.return_value = token

    result = await manager.revoke_refresh_token(db_session, "t")
    assert result is True
    assert token.revoked is True
    db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_revoke_refresh_token_commit_error(manager, db_session):
    """Test revocation handles commit error."""
    token = RefreshToken(
        token="t",
        user_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        created_at=datetime.now(UTC),
        revoked=False,
    )
    db_session._mock_scalars.first.return_value = token
    db_session.commit.side_effect = Exception("db error")

    result = await manager.revoke_refresh_token(db_session, "t")
    assert result is False


@pytest.mark.asyncio
async def test_revoke_refresh_token_db_exception(manager, db_session):
    """Test revocation handles database exception."""
    db_session.execute.side_effect = Exception("db error")

    result = await manager.revoke_refresh_token(db_session, "token")
    assert result is False


# =============================================================================
# DATABASE SESSION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_database_get_session_exception():
    """Test database session handles exception and rolls back."""
    from shared.auth.database import DatabaseManager

    dbm = DatabaseManager("sqlite+aiosqlite:///:memory:")

    class DummyException(Exception):
        pass

    try:
        async with dbm.get_session():
            raise DummyException("fail inside session")
    except DummyException:
        pass  # Should trigger rollback and close


# =============================================================================
# TOKEN VERIFICATION TESTS
# =============================================================================


def test_verify_token_enhanced_missing_claims(manager):
    """Test verify_token_enhanced returns None for missing claims."""
    with patch.object(
        manager,
        "verify_token",
        return_value={
            "sub": "u",
            "user_id": "id",
            "exp": 1,
            "iat": 1,
            "iss": "iss",
            "token_type": "access",
        },
    ):
        assert manager.verify_token_enhanced("token") is None


def test_verify_token_enhanced_tokenpayload_exception(manager):
    """Test verify_token_enhanced handles TokenPayload exception."""
    with (
        patch.object(
            manager,
            "verify_token",
            return_value={
                "sub": "u",
                "user_id": "id",
                "role": "user",
                "exp": 1,
                "iat": 1,
                "iss": "iss",
                "token_type": "access",
            },
        ),
        patch("shared.auth.manager.UserRole", side_effect=Exception("fail")),
    ):
        result = manager.verify_token_enhanced("token")
        assert result is None


@pytest.mark.asyncio
async def test_verify_token_enhanced_all_missing_claims(manager):
    """Test verify_token_enhanced returns None for each missing required claim."""
    required_claims = ["sub", "user_id", "role", "exp", "iat", "iss", "token_type"]
    for missing in required_claims:
        payload = {k: "x" for k in required_claims if k != missing}
        with patch.object(manager, "verify_token", return_value=payload):
            assert manager.verify_token_enhanced("token") is None


# =============================================================================
# REQUEST HANDLING TESTS
# =============================================================================


def test_get_user_from_request_invalid_credentials(manager):
    """Test get_user_from_request raises for invalid credentials."""
    from fastapi.security import HTTPAuthorizationCredentials

    with pytest.raises(HTTPException) as excinfo:
        manager.get_user_from_request(None)
    assert excinfo.value.status_code == 401

    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="token")
    with pytest.raises(HTTPException) as excinfo:
        manager.get_user_from_request(credentials)
    assert excinfo.value.status_code == 401


def test_get_user_from_request_invalid_jwt(manager):
    """Test get_user_from_request raises for invalid JWT."""
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="badtoken")
    with patch.object(manager, "verify_token_enhanced", return_value=None):
        with pytest.raises(HTTPException) as excinfo:
            manager.get_user_from_request(credentials)
        assert excinfo.value.status_code == 401


def test_get_user_from_request_invalid_token(manager):
    """Test get_user_from_request raises for invalid token with proper message."""
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "verify_token_enhanced", return_value=None):
        with pytest.raises(HTTPException) as excinfo:
            manager.get_user_from_request(credentials)
        assert excinfo.value.status_code == 401
        assert "Invalid or expired JWT token" in str(excinfo.value.detail)


def test_requires_roles_forbidden(manager):
    """Test requires_roles raises 403 for insufficient role."""
    from fastapi.security import HTTPAuthorizationCredentials

    dep = manager.requires_roles([UserRole.ADMIN])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    payload = type(
        "Payload",
        (),
        {"has_any_role": lambda _self, _required_roles: False, "roles": []},
    )()
    with patch.object(manager, "get_user_from_request", return_value=payload):
        with pytest.raises(HTTPException) as excinfo:
            dep(credentials)
        assert excinfo.value.status_code == 403


# =============================================================================
# MODULE IMPORT TESTS
# =============================================================================


def test_module_level_dependencies_import():
    """Test module can be imported and reloaded."""
    import importlib

    importlib.reload(__import__("shared.auth.manager"))
