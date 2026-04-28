"""
Integration tests for thread conversation functionality.

Tests multi-turn conversations, thread management, and DiscussionID correlation.

Fully async per ADR-022 (P5-A23 - converted Nov 2025).
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.services.async_history_service import AsyncHistoryService
from src.orchestrator.app.services.context_compaction_service import (
    ContextCompactionService,
)


class TestThreadConversations:
    """Test suite for conversation thread functionality."""

    @pytest_asyncio.fixture
    async def history_service(self, async_db_session: AsyncSession):
        """Create an async history service instance."""
        return AsyncHistoryService(async_db_session)

    @pytest.fixture
    def compaction_service(self):
        """Create a compaction service instance."""
        return ContextCompactionService()

    @pytest.fixture
    def test_user_id(self):
        """Generate a test user ID."""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_create_thread_with_discussion_id(self, history_service, test_user_id):
        """Test creating a thread with DiscussionID."""
        thread = await history_service.create_thread(
            user_id=test_user_id,
            title="IOC Investigation",
            description="Investigating suspicious IP",
            discussion_id="INC-2024-001",
            use_case_name="IOC Analysis",
            source="ui",
        )

        assert thread is not None
        assert thread.title == "IOC Investigation"
        assert thread.discussion_id == "INC-2024-001"
        assert thread.source == "ui"
        assert thread.message_count == 0
        assert thread.context_size_tokens == 0

    @pytest.mark.asyncio
    async def test_list_threads_filter_by_discussion_id(self, history_service, test_user_id):
        """Test listing threads filtered by DiscussionID."""
        # Create threads with different discussion_ids
        await history_service.create_thread(
            user_id=test_user_id,
            title="Thread 1",
            discussion_id="INC-001",
        )
        await history_service.create_thread(
            user_id=test_user_id,
            title="Thread 2",
            discussion_id="INC-001",
        )
        await history_service.create_thread(
            user_id=test_user_id,
            title="Thread 3",
            discussion_id="INC-002",
        )

        # List all threads
        _all_threads, total = await history_service.list_threads()
        assert total >= 3

        # Filter by INC-001
        filtered_threads, filtered_total = await history_service.list_threads(
            discussion_id="INC-001"
        )
        assert filtered_total == 2
        assert all(t.discussion_id == "INC-001" for t in filtered_threads)

    @pytest.mark.asyncio
    async def test_add_thread_message(self, history_service, test_user_id):
        """Test adding messages to a thread."""
        # Create thread
        thread = await history_service.create_thread(
            user_id=test_user_id, title="Test Conversation"
        )

        # Add user message
        msg1 = await history_service.add_thread_message(
            thread_id=thread.id,
            query_id=None,
            role="user",
            content="What is the capital of France?",
            token_count=7,
        )

        assert msg1.sequence_number == 1
        assert msg1.role == "user"
        assert msg1.token_count == 7

        # Add assistant message
        msg2 = await history_service.add_thread_message(
            thread_id=thread.id,
            query_id=None,
            role="assistant",
            content="The capital of France is Paris.",
            token_count=8,
            model_used="gpt-4",
        )

        assert msg2.sequence_number == 2
        assert msg2.role == "assistant"
        assert msg2.model_used == "gpt-4"

        # Verify thread metadata updated
        updated_thread = await history_service.get_thread(thread.thread_id)
        assert updated_thread.message_count == 2
        assert updated_thread.context_size_tokens == 15

    @pytest.mark.asyncio
    async def test_get_thread_messages(self, history_service, test_user_id):
        """Test retrieving thread messages in order."""
        # Create thread and add messages
        thread = await history_service.create_thread(user_id=test_user_id, title="Test Thread")

        for i in range(5):
            await history_service.add_thread_message(
                thread_id=thread.id,
                query_id=None,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}",
                token_count=5,
            )

        # Get messages
        messages = await history_service.get_thread_messages(thread.id)
        assert len(messages) == 5
        assert messages[0].sequence_number == 1
        assert messages[4].sequence_number == 5
        assert messages[0].content == "Message 1"

    def test_token_counting(self, compaction_service):
        """Test token counting with tiktoken."""
        text = "What is the capital of France?"
        token_count = compaction_service.count_tokens(text)

        assert token_count > 0
        assert isinstance(token_count, int)
        # Rough estimate: should be around 7-8 tokens
        assert 5 <= token_count <= 10

    @pytest.mark.asyncio
    async def test_should_compact(self, compaction_service, history_service, test_user_id):
        """Test compaction threshold detection."""
        thread = await history_service.create_thread(user_id=test_user_id, title="Test Thread")

        # Initially should not need compaction
        assert not compaction_service.should_compact(thread)

        # Simulate high token usage (>70% of 8000)
        thread.context_size_tokens = 6000
        assert compaction_service.should_compact(thread)

    @pytest.mark.asyncio
    async def test_find_or_create_thread(self, history_service, test_user_id):
        """Test find_or_create_thread for SOAR integration."""
        discussion_id = "INC-SOAR-001"
        use_case_id = uuid.uuid4()

        # First call: should create thread
        thread1 = await history_service.find_or_create_thread(
            user_id=test_user_id,
            discussion_id=discussion_id,
            use_case_id=use_case_id,
            source="api",
        )

        assert thread1 is not None
        assert thread1.discussion_id == discussion_id
        assert thread1.use_case_id == use_case_id
        assert thread1.source == "api"

        # Second call with same params: should return existing thread
        thread2 = await history_service.find_or_create_thread(
            user_id=test_user_id,
            discussion_id=discussion_id,
            use_case_id=use_case_id,
            source="api",
        )

        assert thread2.id == thread1.id
        assert thread2.thread_id == thread1.thread_id

    @pytest.mark.asyncio
    async def test_update_thread(self, history_service, test_user_id):
        """Test updating thread metadata."""
        thread = await history_service.create_thread(
            user_id=test_user_id,
            title="Original Title",
            discussion_id="INC-001",
        )

        # Update thread
        updated = await history_service.update_thread(
            thread_id=thread.thread_id,
            title="Updated Title",
            discussion_id="INC-002",
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.discussion_id == "INC-002"

    @pytest.mark.asyncio
    async def test_archive_thread(self, history_service, test_user_id):
        """Test archiving a thread."""
        thread = await history_service.create_thread(user_id=test_user_id, title="Test Thread")

        # Archive thread
        success = await history_service.delete_thread(thread_id=thread.thread_id, archive=True)

        assert success is True

        # Verify thread is archived
        archived_thread = await history_service.get_thread(thread.thread_id)
        assert archived_thread.is_active is False
        assert archived_thread.archived_at is not None

    @pytest.mark.asyncio
    async def test_thread_visibility_with_discussion_id(self, history_service, test_user_id):
        """Test that multiple threads can share same DiscussionID."""
        discussion_id = "INC-SHARED-001"

        # Create multiple threads with same discussion_id but different use cases
        await history_service.create_thread(
            user_id=test_user_id,
            title="IOC Analysis",
            discussion_id=discussion_id,
            use_case_name="IOC Analysis",
        )

        await history_service.create_thread(
            user_id=test_user_id,
            title="Log Investigation",
            discussion_id=discussion_id,
            use_case_name="Log Search",
        )

        # List threads by discussion_id
        threads, total = await history_service.list_threads(discussion_id=discussion_id)

        assert total == 2
        assert all(t.discussion_id == discussion_id for t in threads)
        assert {t.title for t in threads} == {"IOC Analysis", "Log Investigation"}
