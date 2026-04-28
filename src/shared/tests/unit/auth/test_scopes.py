"""
Unit tests for scope-based access control.

Tests for:
- TokenPayload.has_scope()
- TokenPayload.has_any_scope()
- requires_scope() dependency
- requires_any_scope() dependency
- Backward compatibility (tokens without scopes)
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from shared.auth.manager import UnifiedAuthManager
from shared.auth.models import TokenPayload, UserRole
from shared.auth.scopes import requires_any_scope, requires_scope

TEST_SECRET = "superstrongtestsecret123!"


@pytest.fixture
def manager():
    """Create test auth manager."""
    return UnifiedAuthManager(secret=TEST_SECRET)


@pytest.fixture
def test_user_id():
    """Generate test user ID."""
    return str(uuid.uuid4())


# ============================================================================
# TokenPayload.has_scope() tests
# ============================================================================


def test_token_payload_has_scope_true():
    """Test has_scope returns True when scope exists."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat", "inference:embeddings"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.has_scope("inference:chat") is True
    assert payload.has_scope("inference:embeddings") is True


def test_token_payload_has_scope_false():
    """Test has_scope returns False when scope does not exist."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.has_scope("inference:embeddings") is False
    assert payload.has_scope("admin:all") is False


def test_token_payload_has_scope_empty_scopes():
    """Test has_scope returns False when scopes list is empty."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=[],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.has_scope("inference:chat") is False


def test_token_payload_backward_compatible_no_scopes():
    """Test backward compatibility - tokens without scopes field should work."""
    # Create token payload without scopes (default should be empty list)
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        # scopes field omitted - should default to []
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.scopes == []
    assert payload.has_scope("any:scope") is False


# ============================================================================
# TokenPayload.has_any_scope() tests
# ============================================================================


def test_token_payload_has_any_scope_true():
    """Test has_any_scope returns True when at least one scope matches."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat", "inference:embeddings"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    # Has one of the required scopes
    assert payload.has_any_scope(["inference:chat", "admin:all"]) is True
    # Has multiple required scopes
    assert payload.has_any_scope(["inference:chat", "inference:embeddings"]) is True


def test_token_payload_has_any_scope_false():
    """Test has_any_scope returns False when no scopes match."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    # Has none of the required scopes
    assert payload.has_any_scope(["admin:all", "corpus:write"]) is False


def test_token_payload_has_any_scope_empty_list():
    """Test has_any_scope returns False with empty required scopes list."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    # Empty required list should return False
    assert payload.has_any_scope([]) is False


def test_token_payload_has_any_scope_empty_token_scopes():
    """Test has_any_scope returns False when token has no scopes."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=[],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.has_any_scope(["inference:chat", "admin:all"]) is False


# ============================================================================
# requires_scope() dependency tests
# ============================================================================


def test_requires_scope_success(manager, test_user_id):
    """Test requires_scope allows request when scope exists."""
    # Create dependency
    dep = requires_scope("inference:chat")

    # Create token payload with required scope
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=["inference:chat", "inference:embeddings"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        result = dep(credentials)
        assert result.sub == "testuser"
        assert result.has_scope("inference:chat")


def test_requires_scope_forbidden(manager, test_user_id):
    """Test requires_scope denies request when scope is missing."""
    # Create dependency
    dep = requires_scope("inference:chat")

    # Create token payload WITHOUT required scope
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=["inference:embeddings"],  # Missing "inference:chat"
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        with pytest.raises(HTTPException) as exc_info:
            dep(credentials)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Missing required scope: inference:chat" in exc_info.value.detail


def test_requires_scope_empty_scopes(manager, test_user_id):
    """Test requires_scope denies request when token has no scopes."""
    # Create dependency
    dep = requires_scope("inference:chat")

    # Create token payload with empty scopes
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=[],  # No scopes
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        with pytest.raises(HTTPException) as exc_info:
            dep(credentials)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# requires_any_scope() dependency tests
# ============================================================================


def test_requires_any_scope_success(manager, test_user_id):
    """Test requires_any_scope allows request when at least one scope matches."""
    # Create dependency requiring any of these scopes
    dep = requires_any_scope(["inference:chat", "inference:embeddings"])

    # Create token payload with one of the required scopes
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=["inference:chat"],  # Has one of the required scopes
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        result = dep(credentials)
        assert result.sub == "testuser"
        assert result.has_any_scope(["inference:chat", "inference:embeddings"])


def test_requires_any_scope_forbidden(manager, test_user_id):
    """Test requires_any_scope denies request when none of the scopes match."""
    # Create dependency
    dep = requires_any_scope(["inference:chat", "inference:embeddings"])

    # Create token payload without any of the required scopes
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=["admin:all"],  # Has none of the required scopes
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        with pytest.raises(HTTPException) as exc_info:
            dep(credentials)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Missing required scopes" in exc_info.value.detail


def test_requires_any_scope_multiple_matches(manager, test_user_id):
    """Test requires_any_scope allows request when token has multiple matching scopes."""
    # Create dependency
    dep = requires_any_scope(["inference:chat", "inference:embeddings"])

    # Create token payload with BOTH required scopes
    payload_obj = TokenPayload(
        sub="testuser",
        user_id=test_user_id,
        role=UserRole.USER,
        scopes=["inference:chat", "inference:embeddings", "admin:all"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )

    # Mock credentials
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    # Mock get_user_from_request on the GLOBAL auth_manager
    from shared.auth.scopes import auth_manager as global_auth_manager

    with patch.object(global_auth_manager, "get_user_from_request", return_value=payload_obj):
        result = dep(credentials)
        assert result.sub == "testuser"


# ============================================================================
# Integration tests with auth_manager
# ============================================================================


def test_requires_scope_with_invalid_token(manager):
    """Test requires_scope properly propagates auth errors."""
    # Create dependency
    dep = requires_scope("inference:chat")

    # Mock credentials with invalid token
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

    # Mock get_user_from_request to raise HTTPException (invalid token)
    with patch.object(
        manager,
        "get_user_from_request",
        side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            dep(credentials)
        # Should get 401 (auth error), not 403 (scope error)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_scope_validation_case_sensitive():
    """Test that scope validation is case-sensitive."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["inference:chat"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    # Case mismatch should fail
    assert payload.has_scope("Inference:Chat") is False
    assert payload.has_scope("INFERENCE:CHAT") is False
    # Exact match should succeed
    assert payload.has_scope("inference:chat") is True


# ============================================================================
# Edge cases and validation
# ============================================================================


def test_token_payload_scopes_is_list():
    """Test that scopes field accepts list type."""
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["scope1", "scope2", "scope3"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert isinstance(payload.scopes, list)
    assert len(payload.scopes) == 3


def test_token_payload_scopes_validation():
    """Test that scopes field validates as list[str]."""
    # Valid scopes
    payload = TokenPayload(
        sub="testuser",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        scopes=["scope1", "scope2"],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    assert payload.scopes == ["scope1", "scope2"]
