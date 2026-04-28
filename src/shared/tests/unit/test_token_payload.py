"""
Unit tests for TokenPayload multi-role support (ADR-060).

Tests the new multi-role methods: has_role(), has_any_role(), has_all_roles()
and backward compatibility with legacy single-role tokens.
"""

from shared.auth.models import TokenPayload


class TestTokenPayloadMultiRole:
    """Test TokenPayload multi-role methods."""

    def test_is_admin_with_admin_role(self):
        """is_admin() returns True when user has admin role."""
        payload = TokenPayload(
            sub="admin",
            user_id="123",
            roles=["admin", "developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.is_admin() is True

    def test_is_admin_without_admin_role(self):
        """is_admin() returns False when user doesn't have admin role."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.is_admin() is False

    def test_has_role_returns_true_when_present(self):
        """has_role() returns True when user has the role."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer", "threat_hunting"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_role("developer") is True
        assert payload.has_role("threat_hunting") is True

    def test_has_role_returns_false_when_absent(self):
        """has_role() returns False when user doesn't have the role."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_role("admin") is False

    def test_has_any_role_returns_true_when_one_present(self):
        """has_any_role() returns True when user has at least one role."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_any_role(["admin", "developer"]) is True

    def test_has_any_role_returns_false_when_none_present(self):
        """has_any_role() returns False when user has none of the roles."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_any_role(["admin", "corpus_admin"]) is False

    def test_has_all_roles_returns_true_when_all_present(self):
        """has_all_roles() returns True when user has all roles."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer", "threat_hunting", "team:csirt"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_all_roles(["developer", "threat_hunting"]) is True

    def test_has_all_roles_returns_false_when_one_missing(self):
        """has_all_roles() returns False when user is missing any role."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=["developer"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.has_all_roles(["developer", "threat_hunting"]) is False

    def test_is_service_with_service_role(self):
        """is_service() returns True when user has service role."""
        payload = TokenPayload(
            sub="service",
            user_id="123",
            roles=["service"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.is_service() is True

    def test_is_service_with_admin_role(self):
        """is_service() returns True when user has admin role."""
        payload = TokenPayload(
            sub="admin",
            user_id="123",
            roles=["admin"],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.is_service() is True

    def test_empty_roles_list(self):
        """TokenPayload with empty roles list works correctly."""
        payload = TokenPayload(
            sub="user",
            user_id="123",
            roles=[],
            exp=1,
            iat=1,
            iss="test",
            token_type="access",
        )
        assert payload.is_admin() is False
        assert payload.has_role("admin") is False
        assert payload.has_any_role(["admin", "developer"]) is False
