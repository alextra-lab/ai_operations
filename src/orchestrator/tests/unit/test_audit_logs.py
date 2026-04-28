"""
Unit tests for audit log API endpoints.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from app.routers.admin_audit import (
    get_audit_log,
    get_audit_stats,
    list_audit_logs,
    require_admin_or_developer,
)
from app.schemas.audit import AuditLogListResponse, AuditLogStatsResponse
from fastapi import HTTPException

from shared.auth.models import TokenPayload


def create_test_token(role: str, username: str = "testuser") -> TokenPayload:
    """Helper to create TokenPayload with all required fields."""
    user_id = str(uuid.uuid4())
    return TokenPayload.model_construct(
        sub=username,
        user_id=user_id,
        username=username,
        role=role,
        exp=datetime.now(UTC) + timedelta(hours=1),
        iat=datetime.now(UTC),
        iss="aio",
        token_type="access",
    )


class TestRequireAdminOrDeveloper:
    """Test authorization helper function."""

    def test_allows_admin(self):
        """Admin should pass authorization."""
        user = create_test_token("admin", "admin")
        # Should not raise
        require_admin_or_developer(user)

    def test_allows_developer(self):
        """Developer should pass authorization."""
        user = create_test_token("developer", "dev")
        # Should not raise
        require_admin_or_developer(user)

    def test_allows_corpus_admin(self):
        """Corpus admin should pass authorization."""
        user = create_test_token("corpus_admin", "corpus")
        # Should not raise
        require_admin_or_developer(user)

    def test_denies_user(self):
        """Regular user should be denied."""
        user = create_test_token("user", "user")
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_developer(user)
        assert exc_info.value.status_code == 403

    def test_denies_analyst(self):
        """Analyst should be denied."""
        user = create_test_token("analyst", "analyst")
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_developer(user)
        assert exc_info.value.status_code == 403


class TestListAuditLogs:
    """Test list_audit_logs endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def admin_user(self):
        """Admin user for testing."""
        return create_test_token("admin", "admin")

    @pytest.fixture
    def sample_audit_log(self):
        """Sample audit log entry."""
        log = Mock()
        log.id = uuid.uuid4()
        log.event_time = datetime.now(UTC)
        log.actor_user_id = uuid.uuid4()
        log.actor_roles = ["admin"]
        log.action = "GET /api/v1/use-cases"
        log.resource_type = "http_request"
        log.resource_id = "/api/v1/use-cases"
        log.use_case_id = None
        log.request_id = "test-request-id"
        log.client_ip = "127.0.0.1"
        log.user_agent = "Test Agent"
        log.success = True
        log.details = {"status_code": 200}
        log.created_at = datetime.now(UTC)
        return log

    @pytest.mark.asyncio
    async def test_list_returns_logs(self, mock_db, admin_user, sample_audit_log):
        """Test successful log listing."""
        # Mock query chain
        query = Mock()
        query.filter.return_value = query
        query.count.return_value = 1
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.all.return_value = [sample_audit_log]

        mock_db.query.return_value = query

        # Mock user query
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = Mock(username="testuser")

        with patch.object(mock_db, "query") as mock_query:
            mock_query.side_effect = [query, user_query, Mock()]

            result = await list_audit_logs(
                page=1, page_size=50, db=mock_db, current_user=admin_user
            )

            assert isinstance(result, AuditLogListResponse)
            assert result.total == 1
            assert len(result.logs) == 1

    @pytest.mark.asyncio
    async def test_list_applies_filters(self, mock_db, admin_user):
        """Test that filters are properly applied."""
        query = Mock()
        query.filter.return_value = query
        query.count.return_value = 0
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.all.return_value = []

        mock_db.query.return_value = query

        test_user_id = uuid.uuid4()
        result = await list_audit_logs(
            page=1,
            page_size=50,
            actor_user_id=test_user_id,
            action="POST",
            resource_type="use_case",
            success=True,
            search="test",
            db=mock_db,
            current_user=admin_user,
        )

        # Verify filters were applied
        assert query.filter.called
        assert result.total == 0


class TestGetAuditStats:
    """Test get_audit_stats endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def admin_user(self):
        """Admin user for testing."""
        return create_test_token("admin", "admin")

    @pytest.mark.asyncio
    async def test_stats_returns_summary(self, mock_db, admin_user):
        """Test successful stats retrieval."""
        # Mock query chain
        query = Mock()
        query.filter.return_value = query
        query.count.return_value = 100
        query.with_entities.return_value = query
        query.distinct.return_value = query
        query.group_by.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = [("action1", 50), ("action2", 30)]

        mock_db.query.return_value = query

        result = await get_audit_stats(db=mock_db, current_user=admin_user)

        assert isinstance(result, AuditLogStatsResponse)
        assert result.total_events == 100

    @pytest.mark.asyncio
    async def test_stats_applies_date_range(self, mock_db, admin_user):
        """Test that date range filters are applied."""
        query = Mock()
        query.filter.return_value = query
        query.count.return_value = 0
        query.with_entities.return_value = query
        query.distinct.return_value = query
        query.group_by.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = []

        mock_db.query.return_value = query

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)

        result = await get_audit_stats(
            start_date=start, end_date=end, db=mock_db, current_user=admin_user
        )

        # Verify date filter was applied
        assert query.filter.called
        assert result.date_range_start == start
        assert result.date_range_end == end


class TestGetAuditLog:
    """Test get_audit_log endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def admin_user(self):
        """Admin user for testing."""
        return create_test_token("admin", "admin")

    @pytest.fixture
    def sample_log(self):
        """Sample audit log."""
        log = Mock()
        log.id = uuid.uuid4()
        log.event_time = datetime.now(UTC)
        log.actor_user_id = uuid.uuid4()
        log.actor_roles = ["admin"]
        log.action = "GET /api/v1/test"
        log.resource_type = "http_request"
        log.resource_id = "/api/v1/test"
        log.use_case_id = None
        log.request_id = "test-id"
        log.client_ip = "127.0.0.1"
        log.user_agent = "Test"
        log.success = True
        log.details = {}
        log.created_at = datetime.now(UTC)
        return log

    @pytest.mark.asyncio
    async def test_get_log_returns_entry(self, mock_db, admin_user, sample_log):
        """Test successful log retrieval."""
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = sample_log

        mock_db.query.return_value = query

        # Mock user query
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = Mock(username="testuser")

        with patch.object(mock_db, "query") as mock_query:
            mock_query.side_effect = [query, user_query]

            result = await get_audit_log(log_id=sample_log.id, db=mock_db, current_user=admin_user)

            assert result.id == str(sample_log.id)
            assert result.action == sample_log.action

    @pytest.mark.asyncio
    async def test_get_log_not_found(self, mock_db, admin_user):
        """Test 404 when log doesn't exist."""
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = None

        mock_db.query.return_value = query

        log_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await get_audit_log(log_id=log_id, db=mock_db, current_user=admin_user)

        assert exc_info.value.status_code == 404
