"""
Unit tests for Admin Audit Router

Tests audit log query endpoints.
P5-A11: Created for async admin_audit router (Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.admin_audit import (
    get_audit_log,
    get_audit_stats,
    list_audit_logs,
    require_admin_or_developer,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user():
    """Mock admin user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="admin",
        user_id="a0000000-0000-0000-0000-000000000001",
        role="admin",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def developer_user():
    """Mock developer user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="developer",
        user_id="b0000000-0000-0000-0000-000000000002",
        role="developer",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def regular_user():
    """Mock regular user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="user",
        user_id="c0000000-0000-0000-0000-000000000003",
        role="user",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def mock_audit_log():
    """Create a mock audit log entry."""
    return Mock(
        id=uuid4(),
        event_time=datetime.now(UTC),
        actor_user_id=uuid4(),
        actor_roles=["admin"],
        action="use_case.execute",
        resource_type="use_case",
        resource_id="test-use-case",
        use_case_id=uuid4(),
        request_id="req-123",
        client_ip="127.0.0.1",
        user_agent="TestClient/1.0",
        success=True,
        details={"key": "value"},
    )


# ============================================================================
# Tests: require_admin_or_developer helper
# ============================================================================


class TestRequireAdminOrDeveloper:
    """Test the authorization helper function."""

    def test_admin_passes(self, admin_user):
        """Admin user passes the check."""
        require_admin_or_developer(admin_user)  # Should not raise

    def test_developer_passes(self, developer_user):
        """Developer user passes the check."""
        require_admin_or_developer(developer_user)  # Should not raise

    def test_corpus_admin_passes(self):
        """Corpus admin user passes the check."""
        now = int(datetime.now(UTC).timestamp())
        corpus_admin = TokenPayload(
            sub="corpus_admin",
            user_id="d0000000-0000-0000-0000-000000000004",
            role="corpus_admin",
            exp=now + 3600,
            iat=now,
            iss="ai-operations-platform",
            token_type="access",
        )
        require_admin_or_developer(corpus_admin)  # Should not raise

    def test_regular_user_raises_403(self, regular_user):
        """Regular user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_developer(regular_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Tests: GET /admin/audit-logs
# ============================================================================


class TestListAuditLogs:
    """Test list_audit_logs endpoint."""

    @pytest.mark.asyncio
    async def test_list_logs_success(self, admin_user, mock_async_db, mock_audit_log):
        """Successfully lists audit logs."""
        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        # Mock logs result
        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = [mock_audit_log]

        # Mock user lookup (returns None - no user found)
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = None

        # Mock use case lookup (returns None)
        mock_uc_result = MagicMock()
        mock_uc_result.scalar_one_or_none.return_value = None

        mock_async_db.execute.side_effect = [
            mock_count_result,
            mock_logs_result,
            mock_user_result,
            mock_uc_result,
        ]

        result = await list_audit_logs(
            page=1,
            page_size=50,
            start_date=None,
            end_date=None,
            actor_user_id=None,
            action=None,
            resource_type=None,
            use_case_id=None,
            success=None,
            search=None,
            db=mock_async_db,
            current_user=admin_user,
        )

        assert result.total == 1
        assert result.page == 1
        assert len(result.logs) == 1
        assert result.logs[0].action == "use_case.execute"

    @pytest.mark.asyncio
    async def test_list_logs_with_filters(self, admin_user, mock_async_db):
        """Tests audit logs filtering."""
        # Mock empty results
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = []

        mock_async_db.execute.side_effect = [mock_count_result, mock_logs_result]

        result = await list_audit_logs(
            page=1,
            page_size=10,
            start_date=datetime.now(UTC) - timedelta(days=7),
            end_date=datetime.now(UTC),
            actor_user_id=uuid4(),
            action="login",
            resource_type="auth",
            use_case_id=None,
            success=True,
            search="test",
            db=mock_async_db,
            current_user=admin_user,
        )

        assert result.total == 0
        assert len(result.logs) == 0

    @pytest.mark.asyncio
    async def test_list_logs_unauthorized(self, regular_user, mock_async_db):
        """Regular user cannot access audit logs."""
        with pytest.raises(HTTPException) as exc_info:
            await list_audit_logs(
                page=1,
                page_size=50,
                start_date=None,
                end_date=None,
                actor_user_id=None,
                action=None,
                resource_type=None,
                use_case_id=None,
                success=None,
                search=None,
                db=mock_async_db,
                current_user=regular_user,
            )
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Tests: GET /admin/audit-logs/stats
# ============================================================================


class TestGetAuditStats:
    """Test get_audit_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, admin_user, mock_async_db):
        """Successfully retrieves audit statistics."""
        # Mock all the count queries
        mock_total = MagicMock()
        mock_total.scalar.return_value = 100

        mock_success = MagicMock()
        mock_success.scalar.return_value = 95

        mock_failure = MagicMock()
        mock_failure.scalar.return_value = 5

        mock_unique_users = MagicMock()
        mock_unique_users.scalar.return_value = 10

        mock_unique_rt = MagicMock()
        mock_unique_rt.scalar.return_value = 5

        # Mock top actions
        mock_top_actions = MagicMock()
        mock_top_actions.fetchall.return_value = [
            ("login", 50),
            ("use_case.execute", 30),
            ("logout", 20),
        ]

        # Mock top resource types
        mock_top_rt = MagicMock()
        mock_top_rt.fetchall.return_value = [
            ("auth", 70),
            ("use_case", 30),
        ]

        mock_async_db.execute.side_effect = [
            mock_total,
            mock_success,
            mock_failure,
            mock_unique_users,
            mock_unique_rt,
            mock_top_actions,
            mock_top_rt,
        ]

        result = await get_audit_stats(
            start_date=None,
            end_date=None,
            actor_user_id=None,
            resource_type=None,
            db=mock_async_db,
            current_user=admin_user,
        )

        assert result.total_events == 100
        assert result.success_count == 95
        assert result.failure_count == 5
        assert result.unique_users == 10
        assert len(result.top_actions) == 3
        assert len(result.top_resource_types) == 2

    @pytest.mark.asyncio
    async def test_get_stats_developer_access(self, developer_user, mock_async_db):
        """Developer can access audit statistics."""
        # Mock minimal responses
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.fetchall.return_value = []

        mock_async_db.execute.return_value = mock_result

        result = await get_audit_stats(
            start_date=None,
            end_date=None,
            actor_user_id=None,
            resource_type=None,
            db=mock_async_db,
            current_user=developer_user,
        )

        assert result.total_events == 0


# ============================================================================
# Tests: GET /admin/audit-logs/{log_id}
# ============================================================================


class TestGetAuditLog:
    """Test get_audit_log endpoint."""

    @pytest.mark.asyncio
    async def test_get_log_success(self, admin_user, mock_async_db, mock_audit_log):
        """Successfully retrieves a single audit log."""
        # Mock log result
        mock_log_result = MagicMock()
        mock_log_result.scalar_one_or_none.return_value = mock_audit_log

        # Mock user lookup
        mock_user = Mock(username="testuser")
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock use case lookup
        mock_uc = Mock()
        mock_uc.name = "Test Use Case"  # Set name as attribute, not param
        mock_uc_result = MagicMock()
        mock_uc_result.scalar_one_or_none.return_value = mock_uc

        mock_async_db.execute.side_effect = [
            mock_log_result,
            mock_user_result,
            mock_uc_result,
        ]

        result = await get_audit_log(
            log_id=mock_audit_log.id,
            db=mock_async_db,
            current_user=admin_user,
        )

        assert result.id == mock_audit_log.id
        assert result.action == "use_case.execute"
        assert result.actor_username == "testuser"
        assert result.use_case_name == "Test Use Case"

    @pytest.mark.asyncio
    async def test_get_log_not_found(self, admin_user, mock_async_db):
        """Returns 404 when audit log not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_audit_log(
                log_id=uuid4(),
                db=mock_async_db,
                current_user=admin_user,
            )
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_log_unauthorized(self, regular_user, mock_async_db):
        """Regular user cannot access audit log."""
        with pytest.raises(HTTPException) as exc_info:
            await get_audit_log(
                log_id=uuid4(),
                db=mock_async_db,
                current_user=regular_user,
            )
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
