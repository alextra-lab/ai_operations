import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from shared.auth.manager import UnifiedAuthManager
from shared.auth.models import TokenPayload, User, UserRole

TEST_SECRET = "superstrongtestsecret123!"


@pytest.fixture
def manager():
    return UnifiedAuthManager(secret=TEST_SECRET)


@pytest.fixture
def fake_user():
    return User(
        id=uuid.uuid4(),
        username="testuser",
        full_name="Test User",
        email="test@example.com",
        hashed_password="hashed",
        role=UserRole.USER,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        last_login=None,
    )


def test_verify_token_enhanced_missing_claim(manager):
    # Missing required claims
    data = {"sub": "user", "user_id": str(uuid.uuid4()), "role": UserRole.USER}
    token = manager.create_access_token(data)
    # Simulate missing claims by patching TokenPayload to raise Exception
    with patch("shared.auth.manager.TokenPayload", side_effect=Exception("missing claims")):
        payload = manager.verify_token_enhanced(token)
        assert payload is None


def test_get_user_from_request_success(manager, fake_user):
    data = {
        "sub": fake_user.username,
        "user_id": str(fake_user.id),
        "role": UserRole.USER,
        "exp": int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "iss": manager.issuer,
        "token_type": "access",
    }
    token = manager.create_access_token(data)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.USER.value],
        exp=data["exp"],
        iat=data["iat"],
        iss=data["iss"],
        token_type=data["token_type"],
    )
    with patch.object(manager, "verify_token_enhanced", return_value=payload_obj):
        payload = manager.get_user_from_request(credentials)
        assert payload.sub == fake_user.username


def test_requires_roles_success(manager, fake_user):
    dep = manager.requires_roles([UserRole.ADMIN])
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.ADMIN.value],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "get_user_from_request", return_value=payload_obj):
        out = dep(credentials)
        assert out.is_admin()
        assert UserRole.ADMIN.value in out.roles


def test_requires_roles_forbidden(manager, fake_user):
    dep = manager.requires_roles([UserRole.ADMIN])
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.USER.value],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "get_user_from_request", return_value=payload_obj):
        with pytest.raises(HTTPException) as excinfo:
            dep(credentials)
        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN


def test_get_current_user(manager, fake_user):
    dep = manager.get_current_user()
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.USER.value],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "get_user_from_request", return_value=payload_obj):
        assert dep(credentials).sub == fake_user.username


def test_admin_required(manager, fake_user):
    dep = manager.admin_required()
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.ADMIN.value],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "get_user_from_request", return_value=payload_obj):
        out = dep(credentials)
        assert out.is_admin()
        assert UserRole.ADMIN.value in out.roles


def test_service_required(manager, fake_user):
    dep = manager.service_required()
    payload_obj = TokenPayload(
        sub=fake_user.username,
        user_id=str(fake_user.id),
        roles=[UserRole.SERVICE.value],
        exp=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
        iat=int(datetime.utcnow().timestamp()),
        iss="ai-operations-platform",
        token_type="access",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch.object(manager, "get_user_from_request", return_value=payload_obj):
        out = dep(credentials)
        assert out.is_service()
        assert UserRole.SERVICE.value in out.roles
