"""
Unit tests for AsyncHistoryService (P5-A13 Async Migration).

Tests async database operations for query history and thread management.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.orchestrator.app.services.async_history_service import AsyncHistoryService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def history_service(mock_async_db):
    """Create an AsyncHistoryService instance with mock db."""
    return AsyncHistoryService(db_session=mock_async_db)


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_history_id():
    """Sample history UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_thread_id():
    """Sample thread UUID."""
    return uuid.uuid4()


# ============================================================================
# save_history Tests
# ============================================================================


class TestSaveHistory:
    """Tests for save_history method."""

    @pytest.mark.asyncio
    async def test_save_history_success(self, history_service, mock_async_db, sample_user_id):
        """Successfully save query history."""
        run_id = "test-run-123"
        query_text = "What is the status?"
        response_text = "The status is OK."
        response_status = "success"

        # Mock the db operations
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        await history_service.save_history(
            run_id=run_id,
            user_id=sample_user_id,
            query_text=query_text,
            response_text=response_text,
            response_status=response_status,
        )

        # Verify db operations were called
        assert mock_async_db.add.called
        assert mock_async_db.commit.called
        assert mock_async_db.refresh.called

    @pytest.mark.asyncio
    async def test_save_history_empty_run_id_raises(self, history_service, sample_user_id):
        """Raise ValueError when run_id is empty."""
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            await history_service.save_history(
                run_id="",
                user_id=sample_user_id,
                query_text="test query",
                response_text="test response",
                response_status="success",
            )

    @pytest.mark.asyncio
    async def test_save_history_empty_query_text_raises(self, history_service, sample_user_id):
        """Raise ValueError when query_text is empty."""
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            await history_service.save_history(
                run_id="test-run-123",
                user_id=sample_user_id,
                query_text="",
                response_text="test response",
                response_status="success",
            )

    @pytest.mark.asyncio
    async def test_save_history_db_error_rollback(
        self, history_service, mock_async_db, sample_user_id
    ):
        """Rollback transaction on database error."""
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock(side_effect=Exception("DB Error"))
        mock_async_db.rollback = AsyncMock()

        with pytest.raises(Exception, match="DB Error"):
            await history_service.save_history(
                run_id="test-run-123",
                user_id=sample_user_id,
                query_text="test query",
                response_text="test response",
                response_status="success",
            )

        mock_async_db.rollback.assert_called_once()


# ============================================================================
# get_history Tests
# ============================================================================


class TestGetHistory:
    """Tests for get_history method."""

    @pytest.mark.asyncio
    async def test_get_history_found(self, history_service, mock_async_db, sample_history_id):
        """Return history record when found."""
        mock_history = Mock(id=sample_history_id)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_history
        mock_async_db.execute.return_value = mock_result

        result = await history_service.get_history(sample_history_id)

        assert result == mock_history
        mock_async_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_not_found(self, history_service, mock_async_db, sample_history_id):
        """Return None when history not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await history_service.get_history(sample_history_id)

        assert result is None


# ============================================================================
# list_history Tests
# ============================================================================


class TestListHistory:
    """Tests for list_history method."""

    @pytest.mark.asyncio
    async def test_list_history_success(self, history_service, mock_async_db):
        """Successfully list history records."""
        mock_history1 = Mock(id=uuid.uuid4())
        mock_history2 = Mock(id=uuid.uuid4())

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2

        # Mock list query
        mock_list_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_history1, mock_history2]
        mock_list_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_count_result, mock_list_result]

        history_list, total = await history_service.list_history(limit=50, offset=0)

        assert len(history_list) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_history_with_filters(self, history_service, mock_async_db):
        """List history with filters applied."""
        use_case_id = uuid.uuid4()

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1

        # Mock list query
        mock_list_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [Mock(id=uuid.uuid4())]
        mock_list_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_count_result, mock_list_result]

        history_list, total = await history_service.list_history(
            limit=50,
            offset=0,
            use_case_id=use_case_id,
            intent_type="QUERY",
            response_status="success",
            search_query="test",
        )

        assert len(history_list) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_history_empty(self, history_service, mock_async_db):
        """Return empty list when no records found."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0

        # Mock list query
        mock_list_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_list_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_count_result, mock_list_result]

        history_list, total = await history_service.list_history()

        assert len(history_list) == 0
        assert total == 0


# ============================================================================
# delete_history Tests
# ============================================================================


class TestDeleteHistory:
    """Tests for delete_history method."""

    @pytest.mark.asyncio
    async def test_delete_history_success(self, history_service, mock_async_db, sample_history_id):
        """Successfully delete history record."""
        mock_history = Mock(id=sample_history_id, user_id=uuid.uuid4())
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_history
        mock_async_db.execute.return_value = mock_result
        mock_async_db.delete = AsyncMock()
        mock_async_db.commit = AsyncMock()

        result = await history_service.delete_history(sample_history_id)

        assert result is True
        mock_async_db.delete.assert_called_once_with(mock_history)
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_history_not_found(
        self, history_service, mock_async_db, sample_history_id
    ):
        """Return False when history not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await history_service.delete_history(sample_history_id)

        assert result is False


# ============================================================================
# update_history Tests
# ============================================================================


class TestUpdateHistory:
    """Tests for update_history method."""

    @pytest.mark.asyncio
    async def test_update_history_success(self, history_service, mock_async_db, sample_history_id):
        """Successfully update history record."""
        mock_history = Mock(id=sample_history_id, user_id=uuid.uuid4())
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_history
        mock_async_db.execute.return_value = mock_result
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        update_data = {"response_status": "error", "response_text": "Updated response"}

        result = await history_service.update_history(sample_history_id, update_data)

        assert result == mock_history
        mock_async_db.commit.assert_called_once()
        mock_async_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_history_not_found(
        self, history_service, mock_async_db, sample_history_id
    ):
        """Return None when history not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await history_service.update_history(
            sample_history_id, {"response_status": "error"}
        )

        assert result is None


# ============================================================================
# fork_query Tests
# ============================================================================


class TestForkQuery:
    """Tests for fork_query method."""

    @pytest.mark.asyncio
    async def test_fork_query_success(
        self, history_service, mock_async_db, sample_history_id, sample_user_id
    ):
        """Successfully fork a query."""
        source_query = Mock(
            id=sample_history_id,
            query_text="Original query",
            query_params={},
            use_case_id=uuid.uuid4(),
            use_case_name="Test Use Case",
            intent_type="QUERY",
            center_id="test-center",
            fork_count=0,
        )

        # Mock get_history
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = source_query
        mock_async_db.execute.return_value = mock_result
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        await history_service.fork_query(
            source_query_id=sample_history_id,
            new_user_id=sample_user_id,
        )

        assert mock_async_db.add.called
        assert mock_async_db.commit.called
        assert source_query.fork_count == 1

    @pytest.mark.asyncio
    async def test_fork_query_source_not_found(
        self, history_service, mock_async_db, sample_history_id, sample_user_id
    ):
        """Raise ValueError when source query not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Source query not found"):
            await history_service.fork_query(
                source_query_id=sample_history_id,
                new_user_id=sample_user_id,
            )


# ============================================================================
# Thread Management Tests
# ============================================================================


class TestCreateThread:
    """Tests for create_thread method."""

    @pytest.mark.asyncio
    async def test_create_thread_success(self, history_service, mock_async_db, sample_user_id):
        """Successfully create a thread."""
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        await history_service.create_thread(
            user_id=sample_user_id,
            title="Test Thread",
            description="Test description",
            source="ui",
        )

        assert mock_async_db.add.called
        assert mock_async_db.commit.called


class TestGetThread:
    """Tests for get_thread method."""

    @pytest.mark.asyncio
    async def test_get_thread_found(self, history_service, mock_async_db, sample_thread_id):
        """Return thread when found."""
        mock_thread = Mock(thread_id=sample_thread_id)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_async_db.execute.return_value = mock_result

        result = await history_service.get_thread(sample_thread_id)

        assert result == mock_thread

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, history_service, mock_async_db, sample_thread_id):
        """Return None when thread not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await history_service.get_thread(sample_thread_id)

        assert result is None


class TestListThreads:
    """Tests for list_threads method."""

    @pytest.mark.asyncio
    async def test_list_threads_success(self, history_service, mock_async_db):
        """Successfully list threads."""
        mock_thread1 = Mock(thread_id=uuid.uuid4())
        mock_thread2 = Mock(thread_id=uuid.uuid4())

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2

        # Mock list query
        mock_list_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_thread1, mock_thread2]
        mock_list_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_count_result, mock_list_result]

        threads, total = await history_service.list_threads(limit=50, offset=0)

        assert len(threads) == 2
        assert total == 2


class TestUpdateThread:
    """Tests for update_thread method."""

    @pytest.mark.asyncio
    async def test_update_thread_success(self, history_service, mock_async_db, sample_thread_id):
        """Successfully update thread."""
        mock_thread = Mock(thread_id=sample_thread_id, user_id=uuid.uuid4())
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_async_db.execute.return_value = mock_result
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        result = await history_service.update_thread(
            thread_id=sample_thread_id,
            title="Updated Title",
        )

        assert result == mock_thread
        assert mock_thread.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_thread_not_found(self, history_service, mock_async_db, sample_thread_id):
        """Return None when thread not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await history_service.update_thread(
            thread_id=sample_thread_id,
            title="Updated Title",
        )

        assert result is None


class TestDeleteThread:
    """Tests for delete_thread method."""

    @pytest.mark.asyncio
    async def test_delete_thread_archive(self, history_service, mock_async_db, sample_thread_id):
        """Archive thread instead of deleting."""
        mock_thread = Mock(thread_id=sample_thread_id, is_active=True, archived_at=None)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_async_db.execute.return_value = mock_result
        mock_async_db.commit = AsyncMock()

        result = await history_service.delete_thread(sample_thread_id, archive=True)

        assert result is True
        assert mock_thread.is_active is False
        assert mock_thread.archived_at is not None

    @pytest.mark.asyncio
    async def test_delete_thread_permanent(self, history_service, mock_async_db, sample_thread_id):
        """Permanently delete thread."""
        mock_thread = Mock(thread_id=sample_thread_id)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_async_db.execute.return_value = mock_result
        mock_async_db.delete = AsyncMock()
        mock_async_db.commit = AsyncMock()

        result = await history_service.delete_thread(sample_thread_id, archive=False)

        assert result is True
        mock_async_db.delete.assert_called_once_with(mock_thread)


class TestGetThreadMessages:
    """Tests for get_thread_messages method."""

    @pytest.mark.asyncio
    async def test_get_thread_messages_success(
        self, history_service, mock_async_db, sample_thread_id
    ):
        """Successfully get thread messages."""
        mock_msg1 = Mock(sequence_number=1)
        mock_msg2 = Mock(sequence_number=2)

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_msg1, mock_msg2]
        mock_result.scalars.return_value = mock_scalars
        mock_async_db.execute.return_value = mock_result

        result = await history_service.get_thread_messages(sample_thread_id)

        assert len(result) == 2


class TestAddThreadMessage:
    """Tests for add_thread_message method."""

    @pytest.mark.asyncio
    async def test_add_thread_message_success(
        self, history_service, mock_async_db, sample_thread_id
    ):
        """Successfully add thread message."""
        # Mock max sequence query
        mock_max_seq_result = Mock()
        mock_max_seq_result.scalar.return_value = 5

        # Mock thread query
        mock_thread = Mock(
            id=sample_thread_id,
            message_count=5,
            context_size_tokens=500,
            last_activity_at=datetime.now(UTC),
        )
        mock_thread_result = Mock()
        mock_thread_result.scalar_one_or_none.return_value = mock_thread

        mock_async_db.execute.side_effect = [mock_max_seq_result, mock_thread_result]
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        await history_service.add_thread_message(
            thread_id=sample_thread_id,
            query_id=None,
            role="user",
            content="Test message",
            token_count=10,
        )

        assert mock_async_db.add.called
        assert mock_async_db.commit.called


class TestFindOrCreateThread:
    """Tests for find_or_create_thread method."""

    @pytest.mark.asyncio
    async def test_find_existing_thread(self, history_service, mock_async_db, sample_user_id):
        """Find existing thread when criteria match."""
        discussion_id = "INC-12345"
        use_case_id = uuid.uuid4()
        existing_thread = Mock(thread_id=uuid.uuid4())

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_thread
        mock_async_db.execute.return_value = mock_result

        result = await history_service.find_or_create_thread(
            user_id=sample_user_id,
            discussion_id=discussion_id,
            use_case_id=use_case_id,
            source="api",
        )

        assert result == existing_thread

    @pytest.mark.asyncio
    async def test_create_new_thread_when_not_found(
        self, history_service, mock_async_db, sample_user_id
    ):
        """Create new thread when no existing thread found."""
        discussion_id = "INC-12345"
        use_case_id = uuid.uuid4()

        # First query returns None (no existing thread)
        mock_find_result = Mock()
        mock_find_result.scalar_one_or_none.return_value = None

        mock_async_db.execute.return_value = mock_find_result
        mock_async_db.add = MagicMock()
        mock_async_db.commit = AsyncMock()
        mock_async_db.refresh = AsyncMock()

        await history_service.find_or_create_thread(
            user_id=sample_user_id,
            discussion_id=discussion_id,
            use_case_id=use_case_id,
            source="api",
        )

        assert mock_async_db.add.called
