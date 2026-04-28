"""
Unit tests for Query History Router (P5-A13 Async Migration).

Tests async endpoints for query history and thread management.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.query_history import (
    create_query_history,
    create_thread,
    delete_query_history,
    delete_thread,
    fork_query,
    get_query_history,
    get_thread,
    get_thread_messages,
    list_query_history,
    list_threads,
    require_transcript_storage,
    update_query_history,
    update_thread,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_async_db():
    """Mock async database session."""
    return AsyncMock()


@pytest.fixture
def mock_history_service():
    """Mock async history service."""
    return AsyncMock()


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
def test_user():
    """Mock test user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="testuser",
        user_id="004b53ae-0d85-45e3-8e6d-f1806baa2640",
        role="user",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def sample_history_id():
    """Sample history UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_thread_id():
    """Sample thread UUID."""
    return uuid.uuid4()


# ============================================================================
# Guard Function Tests
# ============================================================================


class TestRequireTranscriptStorage:
    """Tests for the require_transcript_storage guard function."""

    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    def test_guard_blocks_when_disabled(self):
        """Guard raises 501 when transcript storage is disabled."""
        with pytest.raises(HTTPException) as exc_info:
            require_transcript_storage()

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exc_info.value.detail["error"] == "transcript_storage_disabled"
        assert "ADR-030" in exc_info.value.detail["message"]

    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    def test_guard_allows_when_enabled(self):
        """Guard allows operation when transcript storage is enabled."""
        result = require_transcript_storage()
        assert result is None


# ============================================================================
# list_query_history Tests
# ============================================================================


class TestListQueryHistory:
    """Tests for list_query_history endpoint."""

    @pytest.mark.asyncio
    async def test_list_history_success(self, mock_history_service, test_user):
        """Successfully list query history."""
        mock_history = Mock(
            id=uuid.uuid4(),
            run_id="test-run",
            user_id=uuid.uuid4(),
            query_text="test query",
            response_text="test response",
            response_status="success",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            archived_at=None,  # Required field
            use_case_id=None,
            use_case_name=None,
            intent_type="QUERY",
            query_params={},
            metrics={},
            processing_time_ms=100,
            sources={},
            citations={},
            parent_query_id=None,
            fork_count=0,
            thread_id=None,
            center_id=None,
            metadata_json={},
        )
        mock_history_service.list_history.return_value = ([mock_history], 1)

        result = await list_query_history(
            limit=50,
            offset=0,
            use_case_id=None,
            intent_type=None,
            response_status=None,
            search_query=None,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.total == 1
        assert len(result.items) == 1
        mock_history_service.list_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_history_with_filters(self, mock_history_service, test_user):
        """List history with filters applied."""
        use_case_id = uuid.uuid4()
        mock_history_service.list_history.return_value = ([], 0)

        result = await list_query_history(
            limit=50,
            offset=0,
            use_case_id=use_case_id,
            intent_type="QUERY",
            response_status="success",
            search_query="test",
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.total == 0
        mock_history_service.list_history.assert_called_once_with(
            limit=50,
            offset=0,
            use_case_id=use_case_id,
            intent_type="QUERY",
            response_status="success",
            search_query="test",
        )

    @pytest.mark.asyncio
    async def test_list_history_error(self, mock_history_service, test_user):
        """Return 500 on database error."""
        mock_history_service.list_history.side_effect = Exception("DB Error")

        with pytest.raises(HTTPException) as exc_info:
            await list_query_history(
                limit=50,
                offset=0,
                use_case_id=None,
                intent_type=None,
                response_status=None,
                search_query=None,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# get_query_history Tests
# ============================================================================


class TestGetQueryHistory:
    """Tests for get_query_history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_success(self, mock_history_service, test_user, sample_history_id):
        """Successfully get query history."""
        mock_history = Mock(
            id=sample_history_id,
            run_id="test-run",
            user_id=uuid.uuid4(),
            query_text="test query",
            response_text="test response",
            response_status="success",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            archived_at=None,  # Required field
            use_case_id=None,
            use_case_name=None,
            intent_type="QUERY",
            query_params={},
            metrics={},
            processing_time_ms=100,
            sources={},
            citations={},
            parent_query_id=None,
            fork_count=0,
            thread_id=None,
            center_id=None,
            metadata_json={},
        )
        mock_history_service.get_history.return_value = mock_history

        result = await get_query_history(
            history_id=sample_history_id,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.id == sample_history_id
        mock_history_service.get_history.assert_called_once_with(sample_history_id)

    @pytest.mark.asyncio
    async def test_get_history_not_found(self, mock_history_service, test_user, sample_history_id):
        """Return 404 when history not found."""
        mock_history_service.get_history.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_query_history(
                history_id=sample_history_id,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# delete_query_history Tests
# ============================================================================


class TestDeleteQueryHistory:
    """Tests for delete_query_history endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_delete_history_success(self, mock_history_service, test_user, sample_history_id):
        """Successfully delete query history."""
        mock_history_service.delete_history.return_value = True

        await delete_query_history(
            history_id=sample_history_id,
            history_service=mock_history_service,
            current_user=test_user,
        )

        mock_history_service.delete_history.assert_called_once_with(sample_history_id)

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_delete_history_not_found(
        self, mock_history_service, test_user, sample_history_id
    ):
        """Return 404 when history not found."""
        mock_history_service.delete_history.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_query_history(
                history_id=sample_history_id,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# update_query_history Tests
# ============================================================================


class TestUpdateQueryHistory:
    """Tests for update_query_history endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_update_history_success(self, mock_history_service, test_user, sample_history_id):
        """Successfully update query history."""
        from src.orchestrator.app.schemas.query_history import QueryHistoryUpdate

        mock_history = Mock(
            id=sample_history_id,
            run_id="test-run",
            user_id=uuid.uuid4(),
            query_text="test query",
            response_text="updated response",
            response_status="error",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            archived_at=None,  # Required field
            use_case_id=None,
            use_case_name=None,
            intent_type="QUERY",
            query_params={},
            metrics={},
            processing_time_ms=100,
            sources={},
            citations={},
            parent_query_id=None,
            fork_count=0,
            thread_id=None,
            center_id=None,
            metadata_json={},
        )
        mock_history_service.update_history.return_value = mock_history

        update_data = QueryHistoryUpdate(response_status="error")

        result = await update_query_history(
            history_id=sample_history_id,
            update_data=update_data,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.response_status == "error"


# ============================================================================
# create_query_history Tests
# ============================================================================


class TestCreateQueryHistory:
    """Tests for create_query_history endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_create_history_success(self, mock_history_service, test_user):
        """Successfully create query history."""
        from src.orchestrator.app.schemas.query_history import QueryHistoryCreate

        mock_history = Mock(
            id=uuid.uuid4(),
            run_id="test-run-123",
            user_id=uuid.uuid4(),
            query_text="test query",
            response_text="test response",
            response_status="success",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            archived_at=None,  # Required field
            use_case_id=None,
            use_case_name=None,
            intent_type="QUERY",
            query_params={},
            metrics={},
            processing_time_ms=100,
            sources={},
            citations={},
            parent_query_id=None,
            fork_count=0,
            thread_id=None,
            center_id=None,
            metadata_json={},
        )
        mock_history_service.create_history.return_value = mock_history

        history_data = QueryHistoryCreate(
            query_text="test query",
            response_status="success",
            run_id="test-run-123",
            user_id=uuid.UUID(test_user.user_id),
        )

        result = await create_query_history(
            history_data=history_data,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.run_id == "test-run-123"
        mock_history_service.create_history.assert_called_once()


# ============================================================================
# fork_query Tests
# ============================================================================


class TestForkQuery:
    """Tests for fork_query endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_fork_query_success(self, mock_history_service, test_user, sample_history_id):
        """Successfully fork a query."""
        from src.orchestrator.app.schemas.query_history import ForkQueryRequest

        mock_forked = Mock(
            id=uuid.uuid4(),
            run_id="fork_test-123",
            user_id=uuid.uuid4(),
            query_text="test query",
            response_text=None,
            response_status="pending",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            archived_at=None,  # Required field
            use_case_id=None,
            use_case_name=None,
            intent_type="QUERY",
            query_params={},
            metrics={},
            processing_time_ms=None,
            sources={},
            citations={},
            parent_query_id=sample_history_id,
            fork_count=0,
            thread_id=None,
            center_id=None,
            metadata_json={},
        )
        mock_history_service.fork_query.return_value = mock_forked

        fork_request = ForkQueryRequest(source_query_id=sample_history_id)

        result = await fork_query(
            request=fork_request,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.source_query_id == sample_history_id
        assert result.forked_query.response_status == "pending"

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_fork_query_source_not_found(
        self, mock_history_service, test_user, sample_history_id
    ):
        """Return 404 when source query not found."""
        from src.orchestrator.app.schemas.query_history import ForkQueryRequest

        mock_history_service.fork_query.side_effect = ValueError("Source query not found")

        fork_request = ForkQueryRequest(source_query_id=sample_history_id)

        with pytest.raises(HTTPException) as exc_info:
            await fork_query(
                request=fork_request,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Thread Endpoint Tests
# ============================================================================


class TestCreateThread:
    """Tests for create_thread endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_create_thread_success(self, mock_history_service, test_user):
        """Successfully create a thread."""
        from src.orchestrator.app.schemas.query_history import ThreadCreate

        mock_thread = Mock(
            id=uuid.uuid4(),  # Must be UUID
            thread_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test Thread",
            description=None,
            center_id=None,
            discussion_id=None,
            use_case_id=None,
            use_case_name=None,
            source="ui",
            is_active=True,
            message_count=0,
            context_size_tokens=0,
            max_context_tokens=8000,  # Required field
            first_query_id=None,  # Required field
            last_query_id=None,  # Required field
            last_activity_at=datetime.now(UTC),
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata_json={},
        )
        mock_history_service.create_thread.return_value = mock_thread

        thread_request = ThreadCreate(title="Test Thread")

        result = await create_thread(
            request=thread_request,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.title == "Test Thread"


class TestListThreads:
    """Tests for list_threads endpoint."""

    @pytest.mark.asyncio
    async def test_list_threads_success(self, mock_history_service, test_user):
        """Successfully list threads."""
        mock_thread = Mock(
            id=uuid.uuid4(),  # Must be UUID
            thread_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test Thread",
            description=None,
            center_id=None,
            discussion_id=None,
            use_case_id=None,
            use_case_name=None,
            source="ui",
            is_active=True,
            message_count=0,
            context_size_tokens=0,
            max_context_tokens=8000,  # Required field
            first_query_id=None,  # Required field
            last_query_id=None,  # Required field
            last_activity_at=datetime.now(UTC),
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata_json={},
        )
        mock_history_service.list_threads.return_value = ([mock_thread], 1)

        result = await list_threads(
            limit=50,
            offset=0,
            discussion_id=None,
            use_case_id=None,
            is_active=True,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.total == 1
        assert len(result.items) == 1


class TestGetThread:
    """Tests for get_thread endpoint."""

    @pytest.mark.asyncio
    async def test_get_thread_success(self, mock_history_service, test_user, sample_thread_id):
        """Successfully get a thread."""
        mock_thread = Mock(
            id=uuid.uuid4(),  # Must be UUID
            thread_id=sample_thread_id,
            user_id=uuid.uuid4(),
            title="Test Thread",
            description=None,
            center_id=None,
            discussion_id=None,
            use_case_id=None,
            use_case_name=None,
            source="ui",
            is_active=True,
            message_count=0,
            context_size_tokens=0,
            max_context_tokens=8000,  # Required field
            first_query_id=None,  # Required field
            last_query_id=None,  # Required field
            last_activity_at=datetime.now(UTC),
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata_json={},
        )
        mock_history_service.get_thread.return_value = mock_thread

        result = await get_thread(
            thread_id=sample_thread_id,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.thread_id == sample_thread_id

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, mock_history_service, test_user, sample_thread_id):
        """Return 404 when thread not found."""
        mock_history_service.get_thread.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_thread(
                thread_id=sample_thread_id,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetThreadMessages:
    """Tests for get_thread_messages endpoint."""

    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_history_service, test_user, sample_thread_id):
        """Successfully get thread messages."""
        internal_thread_id = uuid.uuid4()
        mock_thread = Mock(id=internal_thread_id, thread_id=sample_thread_id)
        mock_msg = Mock(
            id=uuid.uuid4(),  # Must be UUID
            thread_id=internal_thread_id,  # Must be UUID
            query_id=None,
            sequence_number=1,
            role="user",
            content="Test message",
            token_count=10,
            model_used=None,
            is_summary=False,  # Required field
            original_message_count=None,  # Required field
            created_at=datetime.now(UTC),
        )
        mock_history_service.get_thread.return_value = mock_thread
        mock_history_service.get_thread_messages.return_value = [mock_msg]

        result = await get_thread_messages(
            thread_id=sample_thread_id,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert len(result) == 1


class TestUpdateThread:
    """Tests for update_thread endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_update_thread_success(self, mock_history_service, test_user, sample_thread_id):
        """Successfully update a thread."""
        from src.orchestrator.app.schemas.query_history import ThreadUpdate

        mock_thread = Mock(
            id=uuid.uuid4(),  # Must be UUID
            thread_id=sample_thread_id,
            user_id=uuid.uuid4(),
            title="Updated Title",
            description=None,
            center_id=None,
            discussion_id=None,
            use_case_id=None,
            use_case_name=None,
            source="ui",
            is_active=True,
            message_count=0,
            context_size_tokens=0,
            max_context_tokens=8000,  # Required field
            first_query_id=None,  # Required field
            last_query_id=None,  # Required field
            last_activity_at=datetime.now(UTC),
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata_json={},
        )
        mock_history_service.update_thread.return_value = mock_thread

        update_data = ThreadUpdate(title="Updated Title")

        result = await update_thread(
            thread_id=sample_thread_id,
            request=update_data,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result.title == "Updated Title"


class TestDeleteThread:
    """Tests for delete_thread endpoint."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_delete_thread_archive(self, mock_history_service, test_user, sample_thread_id):
        """Archive thread successfully."""
        mock_history_service.delete_thread.return_value = True

        result = await delete_thread(
            thread_id=sample_thread_id,
            archive=True,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result["status"] == "archived"
        mock_history_service.delete_thread.assert_called_once_with(
            thread_id=sample_thread_id, archive=True
        )

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_delete_thread_permanent(self, mock_history_service, test_user, sample_thread_id):
        """Permanently delete thread successfully."""
        mock_history_service.delete_thread.return_value = True

        result = await delete_thread(
            thread_id=sample_thread_id,
            archive=False,
            history_service=mock_history_service,
            current_user=test_user,
        )

        assert result["status"] == "deleted"
