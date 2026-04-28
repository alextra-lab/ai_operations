"""
Unit tests for the authentication router (async - ADR-022).

Tests the async auth endpoints: login, refresh, revoke, validate, create_user.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.auth.router import get_db_for_auth, router
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.close = AsyncMock()
    return mock_db


@pytest_asyncio.fixture
async def async_client(mock_async_db):
    """Create an async test client with mocked DB dependency."""

    async def override_get_db():
        yield mock_async_db

    app.dependency_overrides[get_db_for_auth] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.auth.router.authenticate_user_async")
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.store_refresh_token_async")
async def test_login_success(mock_store, mock_jwt, mock_auth, async_client):
    """Test successful login returns access and refresh tokens."""
    user = MagicMock()
    user.username = "alice"
    user.role = "user"
    user.id = "user-uuid-123"
    mock_auth.return_value = user
    mock_jwt.access_token_expire_minutes = 15
    mock_jwt.create_access_token.return_value = "access_token"
    mock_jwt.create_refresh_token.return_value = "refresh_token"
    mock_jwt.verify_token.return_value = {"exp": 1234567890}
    mock_store.return_value = None

    data = {"username": "alice", "password": "pw"}
    response = await async_client.post("/auth/token", data=data)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
@patch("app.auth.router.authenticate_user_async", return_value=None)
async def test_login_fail(mock_auth, async_client):
    """Test failed login returns 401."""
    data = {"username": "bob", "password": "bad"}
    response = await async_client.post("/auth/token", data=data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.validate_refresh_token_async")
async def test_refresh_success(mock_validate, mock_jwt, async_client):
    """Test successful token refresh."""
    user = MagicMock()
    user.username = "alice"
    user.role = "user"
    user.id = "user-uuid-123"
    mock_jwt.verify_token.return_value = {"token_type": "refresh"}
    mock_validate.return_value = user
    mock_jwt.access_token_expire_minutes = 15
    mock_jwt.create_access_token.return_value = "new_access_token"

    response = await async_client.post("/auth/refresh", json={"token": "refresh_token"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "new_access_token"


@pytest.mark.asyncio
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.validate_refresh_token_async", return_value=None)
async def test_refresh_fail_invalid_token(mock_validate, mock_jwt, async_client):
    """Test refresh with invalid token returns 401."""
    mock_jwt.verify_token.return_value = {"token_type": "refresh"}

    response = await async_client.post("/auth/refresh", json={"token": "bad_token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.validate_refresh_token_async")
async def test_refresh_fail_invalid_format(mock_validate, mock_jwt, async_client):
    """Test refresh with invalid token format returns 401."""
    mock_jwt.verify_token.return_value = None

    response = await async_client.post("/auth/refresh", json={"token": "bad_token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "format" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.auth.router.revoke_refresh_token_async", return_value=True)
async def test_revoke_success(mock_revoke, async_client):
    """Test successful token revocation."""
    from app.auth.router import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"username": "alice"}

    response = await async_client.post("/auth/revoke", json={"token": "refresh_token"})

    assert response.status_code == 200
    assert response.json()["message"] == "Token successfully revoked"
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.revoke_refresh_token_async", return_value=False)
async def test_revoke_fail(mock_revoke, async_client):
    """Test failed token revocation returns 400."""
    from app.auth.router import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"username": "alice"}

    response = await async_client.post("/auth/revoke", json={"token": "refresh_token"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid token" in response.json()["detail"]
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_validate_token_success(async_client):
    """Test token validation returns user info."""
    from app.auth.router import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "alice",
        "role": "user",
        "user_id": "user-uuid-123",
    }

    response = await async_client.get("/auth/validate")

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.get_password_hash", return_value="hashed")
@patch("app.auth.router.select")
async def test_create_user_success(mock_select, mock_hash, async_client, mock_async_db):
    """Test successful user creation."""
    from app.auth.router import get_current_user

    # Mock admin user for authentication
    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-id"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Mock the select statement
    mock_select.return_value.where.return_value = MagicMock()

    # Mock DB execute to return no existing user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_async_db.execute = AsyncMock(return_value=mock_result)

    # Set up the mock for add/commit/refresh
    mock_async_db.add = MagicMock()

    # Mock refresh to set the id on the user instance
    async def mock_refresh(obj):
        obj.id = "user-uuid-456"

    mock_async_db.refresh = AsyncMock(side_effect=mock_refresh)

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "bob",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == 200
    assert response.json()["username"] == "bob"
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_user_duplicate(async_client, mock_async_db):
    """Test user creation with duplicate username returns 400."""
    from app.auth.router import get_current_user

    # Mock admin user for authentication
    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-id"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Mock existing user
    existing_user = MagicMock()
    existing_user.username = "bob"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_async_db.execute = AsyncMock(return_value=mock_result)

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "bob",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"]
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_user_missing_username(async_client, mock_async_db):
    """Test user creation with empty username returns 400."""
    from app.auth.router import get_current_user

    # Mock admin user for authentication
    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-id"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "required" in response.json()["detail"]
    app.dependency_overrides.pop(get_current_user, None)


# Enhanced tests for P1-F2 functionality


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.authenticate_user_async")
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.store_refresh_token_async")
async def test_login_success_with_audit_logging(
    mock_store, mock_jwt, mock_auth, mock_audit, async_client
):
    """Test that successful login creates audit log entry."""
    user = MagicMock()
    user.username = "alice"
    user.role = "user"
    user.id = "user-uuid-123"
    mock_auth.return_value = user
    mock_jwt.access_token_expire_minutes = 15
    mock_jwt.create_access_token.return_value = "access_token"
    mock_jwt.create_refresh_token.return_value = "refresh_token"
    mock_jwt.verify_token.return_value = {"exp": 1234567890}
    mock_store.return_value = None
    mock_audit.return_value = AsyncMock()

    data = {"username": "alice", "password": "pw"}
    response = await async_client.post("/auth/token", data=data)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

    # Verify audit log was created for successful login
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "login"
    assert call_args[1]["success"] is True
    assert call_args[1]["actor_user_id"] == "user-uuid-123"


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.authenticate_user_async", return_value=None)
async def test_login_failure_with_audit_logging(mock_auth, mock_audit, async_client):
    """Test that failed login creates audit log entry."""
    mock_audit.return_value = AsyncMock()

    data = {"username": "bob", "password": "bad"}
    response = await async_client.post("/auth/token", data=data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"

    # Verify audit log was created for failed login
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "login"
    assert call_args[1]["success"] is False
    assert call_args[1]["actor_user_id"] is None


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.validate_refresh_token_async")
async def test_refresh_success_with_audit_logging(
    mock_validate, mock_jwt, mock_audit, async_client
):
    """Test that successful token refresh creates audit log entry."""
    user = MagicMock()
    user.username = "alice"
    user.role = "user"
    user.id = "user-uuid-123"
    mock_jwt.verify_token.return_value = {"token_type": "refresh"}
    mock_validate.return_value = user
    mock_jwt.access_token_expire_minutes = 15
    mock_jwt.create_access_token.return_value = "new_access_token"
    mock_audit.return_value = AsyncMock()

    response = await async_client.post("/auth/refresh", json={"token": "refresh_token"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "new_access_token"

    # Verify audit log was created for successful refresh
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "token_refresh"
    assert call_args[1]["success"] is True
    assert call_args[1]["actor_user_id"] == "user-uuid-123"


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.jwt_validator")
@patch("app.auth.router.validate_refresh_token_async", return_value=None)
async def test_refresh_failure_with_audit_logging(
    mock_validate, mock_jwt, mock_audit, async_client
):
    """Test that failed token refresh creates audit log entry."""
    mock_jwt.verify_token.return_value = {"token_type": "refresh"}
    mock_audit.return_value = AsyncMock()

    response = await async_client.post("/auth/refresh", json={"token": "bad_token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid" in response.json()["detail"]

    # Verify audit log was created for failed refresh
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "token_refresh"
    assert call_args[1]["success"] is False


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.revoke_refresh_token_async", return_value=True)
async def test_revoke_success_with_audit_logging(mock_revoke, mock_audit, async_client):
    """Test that successful token revocation creates audit log entry."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "alice",
        "user_id": "user-uuid-123",
        "role": "user",
    }

    response = await async_client.post("/auth/revoke", json={"token": "refresh_token"})

    assert response.status_code == 200
    assert response.json()["message"] == "Token successfully revoked"

    # Verify audit log was created for successful revocation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "token_revoke"
    assert call_args[1]["success"] is True
    assert call_args[1]["actor_user_id"] == "user-uuid-123"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.revoke_refresh_token_async", return_value=False)
async def test_revoke_failure_with_audit_logging(mock_revoke, mock_audit, async_client):
    """Test that failed token revocation creates audit log entry."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "alice",
        "user_id": "user-uuid-123",
        "role": "user",
    }

    response = await async_client.post("/auth/revoke", json={"token": "refresh_token"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid token" in response.json()["detail"]

    # Verify audit log was created for failed revocation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "token_revoke"
    assert call_args[1]["success"] is False
    assert call_args[1]["actor_user_id"] == "user-uuid-123"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
@patch("app.auth.router.get_password_hash", return_value="hashed")
@patch("app.auth.router.select")
async def test_create_user_success_with_audit_logging(
    mock_select, mock_hash, mock_audit, async_client, mock_async_db
):
    """Test that successful user creation creates audit log entry."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "admin",
        "user_id": "admin-uuid-123",
        "role": "admin",
    }

    # Mock the select statement
    mock_select.return_value.where.return_value = MagicMock()

    # Mock DB execute to return no existing user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_async_db.execute = AsyncMock(return_value=mock_result)

    # Set up the mock for add/commit/refresh
    mock_async_db.add = MagicMock()

    # Mock refresh to set the id on the user instance
    async def mock_refresh(obj):
        obj.id = "user-uuid-456"

    mock_async_db.refresh = AsyncMock(side_effect=mock_refresh)

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "bob",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == 200
    assert response.json()["username"] == "bob"

    # Verify audit log was created for successful user creation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "user_create"
    assert call_args[1]["success"] is True
    assert call_args[1]["actor_user_id"] == "admin-uuid-123"
    assert call_args[1]["resource_id"] == "user-uuid-456"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
async def test_create_user_insufficient_permissions_with_audit_logging(
    mock_audit, async_client, mock_async_db
):
    """Test that user creation with insufficient permissions creates audit log entry."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "user",
        "user_id": "user-uuid-123",
        "role": "user",  # Not admin
    }

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "bob",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Admin role required" in response.json()["detail"]

    # Verify audit log was created for failed user creation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "user_create"
    assert call_args[1]["success"] is False
    assert call_args[1]["actor_user_id"] == "user-uuid-123"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
async def test_create_user_duplicate_with_audit_logging(mock_audit, async_client, mock_async_db):
    """Test that duplicate user creation creates audit log entry."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "admin",
        "user_id": "admin-uuid-123",
        "role": "admin",
    }

    # Mock existing user
    existing_user = MagicMock()
    existing_user.username = "bob"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_async_db.execute = AsyncMock(return_value=mock_result)

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "bob",
            "password": "pw",
            "full_name": "Bob B",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"]

    # Verify audit log was created for failed user creation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "user_create"
    assert call_args[1]["success"] is False
    assert call_args[1]["actor_user_id"] == "admin-uuid-123"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_audit_logging_error_handling(async_client, mock_async_db):
    """Test that audit logging errors don't break the main functionality."""
    from app.auth.router import get_current_user

    # Mock audit logging to raise an exception
    with patch("app.auth.router.create_audit_log_entry", side_effect=ValueError("Audit error")):
        app.dependency_overrides[get_current_user] = lambda: {
            "username": "alice",
            "user_id": "user-uuid-123",
            "role": "user",
        }

        with patch("app.auth.router.revoke_refresh_token_async", return_value=True):
            response = await async_client.post("/auth/revoke", json={"token": "refresh_token"})

        # Should still work despite audit logging error
        assert response.status_code == 200
        assert response.json()["message"] == "Token successfully revoked"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_user_testuser_reserved(async_client, mock_async_db):
    """Test that 'testuser' username is reserved and returns 400."""
    from app.auth.router import get_current_user

    # Mock admin user for authentication
    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-id"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "testuser",
            "password": "pw",
            "full_name": "Test User",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"]
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
async def test_create_user_testuser_reserved_with_audit(mock_audit, async_client, mock_async_db):
    """Test that 'testuser' username reservation creates audit log."""
    from app.auth.router import get_current_user

    mock_audit.return_value = AsyncMock()

    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-uuid-123"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "TestUser",  # Case-insensitive check
            "password": "pw",
            "full_name": "Test User",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[1]["action"] == "user_create"
    assert call_args[1]["success"] is False
    assert "testuser_reserved" in str(call_args[1]["details"])
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@patch("app.auth.router.create_audit_log_entry")
async def test_create_user_database_error(mock_audit, async_client, mock_async_db):
    """Test that database errors during user creation return 500."""
    from app.auth.router import get_current_user, get_db_for_auth

    admin_user = {"username": "admin", "role": "admin", "user_id": "admin-uuid-123"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Mock that user doesn't exist
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_async_db.execute = AsyncMock(return_value=mock_result)

    # Make commit raise an exception
    mock_async_db.commit = AsyncMock(side_effect=Exception("Database connection lost"))
    mock_async_db.add = MagicMock()

    async def mock_get_db():
        yield mock_async_db

    app.dependency_overrides[get_db_for_auth] = mock_get_db
    mock_audit.return_value = AsyncMock()

    response = await async_client.post(
        "/auth/users/",
        params={
            "username": "newuser",
            "password": "securepassword",
            "full_name": "New User",
            "role": "user",
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "database error" in response.json()["detail"]

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_for_auth, None)
