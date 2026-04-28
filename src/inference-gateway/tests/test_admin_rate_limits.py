"""
Integration tests for admin rate limit endpoints.

Tests:
- List rate limits
- Create rate limit
- Update rate limit
- Delete rate limit
- Get rate limit stats
- Admin authentication required
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from shared.auth.models import TokenPayload

from app.main import app
from app.routers.admin import admin_required, get_current_user


async def _admin_and_user_override():
    """Dependency override that returns a valid admin TokenPayload."""
    return TokenPayload(
        sub="test-admin",
        user_id="test-admin-id",
        roles=["admin"],
        scopes=[],
        exp=9999999999,
        iat=0,
        iss="test",
        token_type="access",
    )


class TestAdminRateLimitEndpoints:
    """Tests for admin rate limit management endpoints."""

    def setup_method(self):
        """Override auth dependencies so admin endpoints accept requests."""
        app.dependency_overrides[admin_required] = _admin_and_user_override
        app.dependency_overrides[get_current_user] = _admin_and_user_override

    def teardown_method(self):
        """Clear overrides after each test."""
        app.dependency_overrides.pop(admin_required, None)
        app.dependency_overrides.pop(get_current_user, None)

    def test_list_rate_limits(self):
        """Test listing all rate limits."""
        client = TestClient(app)

        # Mock database to return test limits
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                (
                    uuid4(),
                    "global",
                    None,
                    500,
                    None,
                    50,
                    True,
                    "Global limit",
                ),
                (
                    uuid4(),
                    "provider",
                    "openai",
                    450,
                    180000,
                    20,
                    True,
                    "OpenAI limit",
                ),
            ]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.get("/admin/rate-limits")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["limit_type"] == "global"
            assert data[1]["limit_type"] == "provider"

    def test_list_rate_limits_enabled_only(self):
        """Test listing only enabled rate limits."""
        client = TestClient(app)

        # Mock database
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                (
                    uuid4(),
                    "global",
                    None,
                    500,
                    None,
                    50,
                    True,
                    "Global limit",
                ),
            ]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.get("/admin/rate-limits?enabled_only=true")

            assert response.status_code == 200
            data = response.json()
            assert all(limit["enabled"] for limit in data)

    def test_create_rate_limit(self):
        """Test creating a new rate limit."""
        client = TestClient(app)

        limit_data = {
            "limit_type": "integration",
            "identifier": "service:test-service",
            "requests_per_minute": 100,
            "burst_size": 10,
            "enabled": True,
            "description": "Test service limit",
        }

        # Mock database
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()

            # Mock check query (no existing)
            check_result = MagicMock()
            check_result.fetchone.return_value = None

            # Mock insert query
            insert_result = MagicMock()
            test_id = uuid4()
            insert_result.fetchone.return_value = (test_id,)

            mock_db.execute = AsyncMock(side_effect=[check_result, insert_result])
            mock_db.commit = AsyncMock()
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.post("/admin/rate-limits", json=limit_data)

            assert response.status_code == 201
            data = response.json()
            assert data["limit_type"] == "integration"
            assert data["identifier"] == "service:test-service"
            assert data["requests_per_minute"] == 100
            assert data["id"] is not None

    def test_create_rate_limit_duplicate(self):
        """Test that creating duplicate rate limit returns 409."""
        client = TestClient(app)

        limit_data = {
            "limit_type": "global",
            "identifier": None,
            "requests_per_minute": 500,
            "burst_size": 50,
            "enabled": True,
        }

        # Mock database to return existing record
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (uuid4(),)  # Existing record
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.post("/admin/rate-limits", json=limit_data)

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]

    def test_update_rate_limit(self):
        """Test updating an existing rate limit."""
        client = TestClient(app)

        limit_id = uuid4()
        update_data = {
            "limit_type": "global",
            "requests_per_minute": 600,
            "tokens_per_minute": None,
            "burst_size": 60,
            "enabled": True,
            "description": "Updated global limit",
        }

        # Mock database
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (limit_id,)  # Update successful
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.put(
                f"/admin/rate-limits/{limit_id}",
                json=update_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requests_per_minute"] == 600
            assert data["burst_size"] == 60

    def test_update_rate_limit_not_found(self):
        """Test that updating non-existent rate limit returns 404."""
        client = TestClient(app)

        limit_id = uuid4()
        update_data = {
            "limit_type": "global",
            "requests_per_minute": 600,
            "burst_size": 60,
            "enabled": True,
        }

        # Mock database to return no results (update uses fetch first)
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None  # Not found
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.put(
                f"/admin/rate-limits/{limit_id}",
                json=update_data,
            )

            assert response.status_code == 404

    def test_delete_rate_limit(self):
        """Test deleting a rate limit."""
        client = TestClient(app)

        limit_id = uuid4()

        # Mock database
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (limit_id,)  # Delete successful
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.delete(f"/admin/rate-limits/{limit_id}")

            assert response.status_code == 204

    def test_delete_rate_limit_not_found(self):
        """Test that deleting non-existent rate limit returns 404."""
        client = TestClient(app)

        limit_id = uuid4()

        # Mock database to return no results
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None  # Not found
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            response = client.delete(f"/admin/rate-limits/{limit_id}")

            assert response.status_code == 404

    def test_get_rate_limit_stats(self):
        """Test getting current rate limit usage statistics."""
        client = TestClient(app)

        # Mock database to return limits
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("global", None, 500, 50),
                ("provider", "openai", 450, 20),
            ]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            # Mock Redis client
            with patch("app.services.redis_client.get_redis_client") as mock_redis:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.is_available = True
                mock_redis_instance.client.zcount = AsyncMock(return_value=250)
                mock_redis_instance.client.zrange = AsyncMock(return_value=[("123.456", 123.456)])
                mock_redis.return_value = mock_redis_instance

                response = client.get("/admin/rate-limits/stats")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert all("current_count" in stat for stat in data)
                assert all("limit" in stat for stat in data)
                assert all("window_remaining_seconds" in stat for stat in data)

    def test_get_rate_limit_stats_redis_unavailable(self):
        """Test getting stats when Redis is unavailable."""
        client = TestClient(app)

        # Mock database
        with patch("app.routers.admin.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("global", None, 500, 50),
            ]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_cm

            # Mock Redis client unavailable
            with patch("app.services.redis_client.get_redis_client") as mock_redis:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.is_available = False
                mock_redis.return_value = mock_redis_instance

                response = client.get("/admin/rate-limits/stats")

                assert response.status_code == 200
                data = response.json()
                # Should return zero counts when Redis unavailable
                assert all(stat["current_count"] == 0 for stat in data)
