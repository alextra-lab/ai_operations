from datetime import timedelta

import pytest

from shared.auth.base import AuthManager

TEST_SECRET = "superstrongtestsecret123!"


def test_authmanager_init_with_valid_secret():
    manager = AuthManager(secret=TEST_SECRET)
    assert manager.secret == TEST_SECRET


def test_authmanager_init_with_env_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    manager = AuthManager()
    assert manager.secret == TEST_SECRET


def test_authmanager_init_with_insecure_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "mysecretkey")
    with pytest.raises(RuntimeError):
        AuthManager()


def test_create_access_token_and_verify():
    manager = AuthManager(secret=TEST_SECRET)
    data = {"sub": "user1"}
    token = manager.create_access_token(data)
    payload = manager.verify_token(token)
    assert payload["sub"] == "user1"
    assert payload["token_type"] == "access"
    assert payload["iss"] == manager.issuer


def test_create_refresh_token_and_verify():
    manager = AuthManager(secret=TEST_SECRET)
    data = {"sub": "user2"}
    token = manager.create_refresh_token(data)
    payload = manager.verify_token(token)
    assert payload["sub"] == "user2"
    assert payload["token_type"] == "refresh"
    assert payload["iss"] == manager.issuer


def test_access_token_expiry():
    manager = AuthManager(secret=TEST_SECRET, access_token_expire_minutes=0)
    data = {"sub": "user3"}
    token = manager.create_access_token(data, expires_delta=timedelta(seconds=-1))
    # Token should be expired
    assert manager.verify_token(token) is None


def test_verify_token_invalid():
    manager = AuthManager(secret=TEST_SECRET)
    # Invalid token
    assert manager.verify_token("not.a.jwt") is None
    # Token with wrong secret
    other_manager = AuthManager(secret="othersecret")
    token = other_manager.create_access_token({"sub": "user4"})
    assert manager.verify_token(token) is None
