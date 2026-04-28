"""
Async History Service for AI Operations Platform.

This service provides async functionality to manage query history, including:
- Saving query execution history
- Retrieving historical queries
- Deleting query history records
- Forking queries
- Managing conversation threads

P5-A13: Async SQLAlchemy migration (Nov 2025).

The AsyncHistoryService handles all database operations related to query history
and provides RLS-aware access control through SQLAlchemy async session.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import get_logger

from ..db.models import ContextThread, QueryHistory, ThreadMessage
from ..schemas.query_history import QueryHistoryCreate

logger = get_logger(__name__)


class AsyncHistoryService:
    """
    Async service for managing query history and conversation threads.

    This service provides methods to:
    - Save query execution history
    - Retrieve history with filtering and pagination
    - Fork queries for reuse
    - Manage conversation threads
    - Apply RLS policies for user isolation

    All methods are async and use SQLAlchemy 2.x async patterns.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the history service with an async database session.

        Args:
            db_session: SQLAlchemy async database session with RLS configured
        """
        self.db_session = db_session

    async def save_history(
        self,
        run_id: str,
        user_id: uuid.UUID,
        query_text: str,
        response_text: str | None,
        response_status: str,
        use_case_id: uuid.UUID | None = None,
        use_case_name: str | None = None,
        intent_type: str | None = None,
        query_params: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        processing_time_ms: int | None = None,
        sources: dict[str, Any] | None = None,
        citations: dict[str, Any] | None = None,
        parent_query_id: uuid.UUID | None = None,
        thread_id: uuid.UUID | None = None,
        center_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QueryHistory:
        """
        Save query execution history to database.

        Args:
            run_id: Unique run identifier from orchestrator
            user_id: UUID of the user who executed the query
            query_text: The original query text
            response_text: The response text from the LLM
            response_status: Status of the response (success, error, etc.)
            use_case_id: Optional UUID of the use case
            use_case_name: Optional name of the use case
            intent_type: Optional intent type (QUERY, SUMMARIZATION, etc.)
            query_params: Optional query parameters
            metrics: Optional execution metrics
            processing_time_ms: Optional execution time in milliseconds
            sources: Optional retrieved sources
            citations: Optional citations
            parent_query_id: Optional parent query UUID for forks
            thread_id: Optional thread UUID for conversation threads
            center_id: Optional center identifier
            metadata: Optional additional metadata

        Returns:
            QueryHistory: The created query history record

        Raises:
            ValueError: If required fields are missing
            Exception: If database error occurs
        """
        if not run_id:
            raise ValueError("run_id cannot be empty")
        if not query_text:
            raise ValueError("query_text cannot be empty")

        try:
            # Create history record
            history_kwargs = {
                "run_id": run_id,
                "user_id": user_id,
                "center_id": center_id,
                "use_case_id": use_case_id,
                "use_case_name": use_case_name,
                "intent_type": intent_type,
                "query_text": query_text,
                "query_params": query_params or {},
                "response_text": response_text,
                "response_status": response_status,
                "metrics": metrics or {},
                "processing_time_ms": processing_time_ms,
                "sources": sources or {},
                "citations": citations or {},
                "parent_query_id": parent_query_id,
                "thread_id": thread_id,
                "metadata_json": metadata or {},
            }
            history = QueryHistory(**history_kwargs)  # type: ignore

            self.db_session.add(history)
            await self.db_session.commit()
            await self.db_session.refresh(history)

            logger.info(
                "Saved query history",
                extra={
                    "run_id": run_id,
                    "user_id": str(user_id),
                    "use_case_id": str(use_case_id) if use_case_id else None,
                    "response_status": response_status,
                },
            )

            return history

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error saving query history for run_id %s: %s", run_id, str(e))
            raise

    async def create_history(
        self, user_id: uuid.UUID, history_data: QueryHistoryCreate
    ) -> QueryHistory:
        """
        Create new query history record.

        Args:
            user_id: UUID of the user creating the history
            history_data: Query history creation data

        Returns:
            QueryHistory: The created query history record

        Raises:
            ValueError: If required fields are missing
            Exception: If database error occurs
        """
        if not history_data.query_text:
            raise ValueError("query_text cannot be empty")
        if not history_data.run_id:
            raise ValueError("run_id cannot be empty")

        try:
            # Create history record from the provided data
            history_kwargs = {
                "run_id": history_data.run_id,
                "user_id": user_id,
                "center_id": history_data.center_id,
                "use_case_id": history_data.use_case_id,
                "use_case_name": history_data.use_case_name,
                "intent_type": history_data.intent_type,
                "query_text": history_data.query_text,
                "query_params": history_data.query_params or {},
                "response_text": history_data.response_text,
                "response_status": history_data.response_status,
                "metrics": history_data.metrics or {},
                "processing_time_ms": history_data.processing_time_ms,
                "sources": history_data.sources or {},
                "citations": history_data.citations or {},
                "parent_query_id": history_data.parent_query_id,
                "thread_id": history_data.thread_id,
                "metadata_json": history_data.metadata or {},
            }
            history = QueryHistory(**history_kwargs)  # type: ignore

            self.db_session.add(history)
            await self.db_session.commit()
            await self.db_session.refresh(history)

            logger.info(
                "Created query history",
                extra={
                    "run_id": history_data.run_id,
                    "user_id": str(user_id),
                    "history_id": str(history.id),
                    "intent_type": history_data.intent_type,
                },
            )

            return history

        except Exception as e:
            await self.db_session.rollback()
            logger.error(
                "Error creating query history for run_id %s: %s",
                history_data.run_id,
                str(e),
            )
            raise

    async def get_history(
        self,
        history_id: uuid.UUID,
    ) -> QueryHistory | None:
        """
        Get a single query history record by ID.

        RLS policies automatically filter to current user's records only.

        Args:
            history_id: UUID of the history record

        Returns:
            QueryHistory record if found and accessible, None otherwise
        """
        try:
            stmt = select(QueryHistory).where(QueryHistory.id == history_id)
            result = await self.db_session.execute(stmt)
            history = result.scalar_one_or_none()

            if history:
                logger.debug("Retrieved history record: %s", history_id)
            else:
                logger.debug("History record not found or not accessible: %s", history_id)

            return history

        except Exception as e:
            logger.error("Error retrieving history %s: %s", history_id, str(e))
            raise

    async def get_history_by_run_id(
        self,
        run_id: str,
    ) -> QueryHistory | None:
        """
        Get a query history record by run_id.

        Args:
            run_id: The unique run identifier

        Returns:
            QueryHistory record if found, None otherwise
        """
        try:
            stmt = select(QueryHistory).where(QueryHistory.run_id == run_id)
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Error retrieving history by run_id %s: %s", run_id, str(e))
            raise

    async def list_history(
        self,
        limit: int = 50,
        offset: int = 0,
        use_case_id: uuid.UUID | None = None,
        intent_type: str | None = None,
        response_status: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[QueryHistory], int]:
        """
        List query history with filtering and pagination.

        RLS policies automatically filter to current user's records.

        Args:
            limit: Maximum number of records to return (default 50)
            offset: Number of records to skip (default 0)
            use_case_id: Optional filter by use case UUID
            intent_type: Optional filter by intent type
            response_status: Optional filter by response status
            search_query: Optional full-text search on query_text

        Returns:
            Tuple of (list of QueryHistory records, total count)
        """
        try:
            # Build filter conditions
            conditions = []

            if use_case_id:
                conditions.append(QueryHistory.use_case_id == use_case_id)

            if intent_type:
                conditions.append(QueryHistory.intent_type == intent_type)

            if response_status:
                conditions.append(QueryHistory.response_status == response_status)

            if search_query:
                conditions.append(QueryHistory.query_text.ilike(f"%{search_query}%"))

            # Get total count
            count_stmt = select(func.count(QueryHistory.id))  # type: ignore[misc,call-arg]
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            count_result = await self.db_session.execute(count_stmt)
            total_count = count_result.scalar() or 0

            # Build main query with pagination
            stmt = select(QueryHistory)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.order_by(desc(QueryHistory.created_at)).limit(limit).offset(offset)

            result = await self.db_session.execute(stmt)
            history_list = list(result.scalars().all())

            logger.info(
                "Listed history",
                extra={
                    "count": len(history_list),
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                },
            )

            return history_list, total_count

        except Exception as e:
            logger.error("Error listing history: %s", str(e))
            raise

    async def update_history(
        self,
        history_id: uuid.UUID,
        update_data: dict[str, Any],
    ) -> QueryHistory | None:
        """
        Update a query history record by ID.

        RLS policies automatically ensure users can only update their own records.

        Args:
            history_id: UUID of the history record to update
            update_data: Dictionary of fields to update

        Returns:
            QueryHistory: Updated record if found and accessible, None otherwise

        Raises:
            Exception: If database error occurs
        """
        try:
            # Get the history record (RLS will filter to user's records)
            history = await self.get_history(history_id)

            if not history:
                logger.warning(
                    "History record not found or not accessible for update: %s",
                    history_id,
                )
                return None

            # Update only provided fields
            update_fields = {}

            if update_data.get("response_text") is not None:
                history.response_text = update_data["response_text"]
                update_fields["response_text"] = True

            if update_data.get("response_status") is not None:
                history.response_status = update_data["response_status"]
                update_fields["response_status"] = True

            if update_data.get("metrics") is not None:
                history.metrics = update_data["metrics"]
                update_fields["metrics"] = True

            if update_data.get("processing_time_ms") is not None:
                history.processing_time_ms = update_data["processing_time_ms"]
                update_fields["processing_time_ms"] = True

            if update_data.get("sources") is not None:
                history.sources = update_data["sources"]
                update_fields["sources"] = True

            if update_data.get("citations") is not None:
                history.citations = update_data["citations"]
                update_fields["citations"] = True

            if update_data.get("metadata") is not None:
                history.metadata_json = update_data["metadata"]
                update_fields["metadata"] = True

            # Commit changes
            await self.db_session.commit()
            await self.db_session.refresh(history)

            logger.info(
                "Updated query history",
                extra={
                    "history_id": str(history_id),
                    "user_id": str(history.user_id),
                    "updated_fields": list(update_fields.keys()),
                },
            )

            return history

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error updating history %s: %s", history_id, str(e))
            raise

    async def delete_history(
        self,
        history_id: uuid.UUID,
    ) -> bool:
        """
        Delete a query history record by ID.

        RLS policies automatically ensure users can only delete their own records.

        Args:
            history_id: UUID of the history record to delete

        Returns:
            bool: True if record was deleted, False if not found or not accessible

        Raises:
            Exception: If database error occurs
        """
        try:
            # Get the history record (RLS will filter to user's records)
            history = await self.get_history(history_id)

            if not history:
                logger.warning(
                    "History record not found or not accessible for deletion: %s",
                    history_id,
                )
                return False

            # Delete the record
            await self.db_session.delete(history)
            await self.db_session.commit()

            logger.info(
                "Deleted query history",
                extra={
                    "history_id": str(history_id),
                    "user_id": str(history.user_id),
                },
            )

            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error deleting history %s: %s", history_id, str(e))
            raise

    async def fork_query(
        self,
        source_query_id: uuid.UUID,
        new_user_id: uuid.UUID,
    ) -> QueryHistory:
        """
        Fork a query by creating a copy with parent link.

        This creates a new history record with:
        - Same query_text and query_params
        - Same use_case_id and intent_type
        - Parent link to source query
        - New run_id and new user
        - Status set to 'pending'

        Args:
            source_query_id: UUID of the source query to fork
            new_user_id: UUID of the user creating the fork

        Returns:
            QueryHistory: The newly created forked query

        Raises:
            ValueError: If source query not found
            Exception: If database error occurs
        """
        try:
            # Get source query
            source_query = await self.get_history(source_query_id)

            if not source_query:
                raise ValueError(f"Source query not found: {source_query_id}")

            # Generate new run_id
            new_run_id = f"fork_{uuid.uuid4()}"

            # Create forked query
            forked_kwargs = {
                "run_id": new_run_id,
                "user_id": new_user_id,
                "center_id": source_query.center_id,
                "use_case_id": source_query.use_case_id,
                "use_case_name": source_query.use_case_name,
                "intent_type": source_query.intent_type,
                "query_text": source_query.query_text,
                "query_params": source_query.query_params,
                "parent_query_id": source_query_id,
                "response_status": "pending",
                "metadata_json": {
                    "forked_from": str(source_query_id),
                    "forked_at": datetime.now(tz=UTC).isoformat(),
                },
            }
            forked_query = QueryHistory(**forked_kwargs)  # type: ignore

            self.db_session.add(forked_query)

            # Increment fork count on source
            source_query.fork_count += 1

            await self.db_session.commit()
            await self.db_session.refresh(forked_query)

            logger.info(
                "Forked query",
                extra={
                    "source_query_id": str(source_query_id),
                    "new_query_id": str(forked_query.id),
                    "new_run_id": new_run_id,
                },
            )

            return forked_query

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error forking query %s: %s", source_query_id, str(e))
            raise

    # =========================================================================
    # Thread Management Methods
    # =========================================================================

    async def create_thread(
        self,
        user_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        center_id: str | None = None,
        discussion_id: str | None = None,
        use_case_id: uuid.UUID | None = None,
        use_case_name: str | None = None,
        source: str = "ui",
        metadata: dict[str, Any] | None = None,
    ) -> ContextThread:
        """
        Create a new conversation thread.

        Args:
            user_id: UUID of the user creating the thread
            title: Optional title for the thread
            description: Optional description
            center_id: Optional center identifier
            discussion_id: Optional external incident/ticket ID
            use_case_id: Optional associated use case UUID
            use_case_name: Optional use case name
            source: Source of thread creation (ui, api, soar)
            metadata: Optional additional metadata

        Returns:
            ContextThread: The created thread
        """
        try:
            thread_kwargs = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "center_id": center_id,
                "discussion_id": discussion_id,
                "use_case_id": use_case_id,
                "use_case_name": use_case_name,
                "source": source,
                "metadata_json": metadata or {},
            }
            thread = ContextThread(**thread_kwargs)  # type: ignore

            self.db_session.add(thread)
            await self.db_session.commit()
            await self.db_session.refresh(thread)

            logger.info(
                "Created conversation thread",
                extra={
                    "thread_id": str(thread.thread_id),
                    "user_id": str(user_id),
                    "discussion_id": discussion_id,
                    "source": source,
                },
            )

            return thread

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error creating thread: %s", str(e))
            raise

    async def get_thread(
        self,
        thread_id: uuid.UUID,
    ) -> ContextThread | None:
        """
        Get a conversation thread by ID.

        Args:
            thread_id: UUID of the thread

        Returns:
            ContextThread if found, None otherwise
        """
        try:
            stmt = select(ContextThread).where(ContextThread.thread_id == thread_id)
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Error retrieving thread %s: %s", thread_id, str(e))
            raise

    async def list_threads(
        self,
        limit: int = 50,
        offset: int = 0,
        discussion_id: str | None = None,
        use_case_id: uuid.UUID | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[ContextThread], int]:
        """
        List conversation threads with optional filters.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            discussion_id: Optional filter by discussion ID
            use_case_id: Optional filter by use case UUID
            is_active: Optional filter by active status

        Returns:
            Tuple of (list of threads, total count)
        """
        try:
            # Build filter conditions
            conditions = []

            if discussion_id:
                conditions.append(ContextThread.discussion_id == discussion_id)

            if use_case_id:
                conditions.append(ContextThread.use_case_id == use_case_id)

            if is_active is not None:
                conditions.append(ContextThread.is_active == is_active)

            # Get total count
            count_stmt = select(func.count(ContextThread.id))  # type: ignore[misc,call-arg]
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            count_result = await self.db_session.execute(count_stmt)
            total = count_result.scalar() or 0

            # Build main query
            stmt = select(ContextThread)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.order_by(desc(ContextThread.last_activity_at)).limit(limit).offset(offset)

            result = await self.db_session.execute(stmt)
            threads = list(result.scalars().all())

            logger.info(
                "Listed threads",
                extra={
                    "count": len(threads),
                    "total": total,
                    "discussion_id": discussion_id,
                },
            )

            return threads, total

        except Exception as e:
            logger.error("Error listing threads: %s", str(e))
            raise

    async def update_thread(
        self,
        thread_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        discussion_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextThread | None:
        """
        Update a conversation thread.

        Args:
            thread_id: UUID of the thread to update
            title: Optional new title
            description: Optional new description
            is_active: Optional active status
            discussion_id: Optional new discussion ID
            metadata: Optional new metadata

        Returns:
            Updated thread if found, None otherwise
        """
        try:
            thread = await self.get_thread(thread_id)

            if not thread:
                logger.warning("Thread not found or not accessible: %s", thread_id)
                return None

            if title is not None:
                thread.title = title
            if description is not None:
                thread.description = description
            if is_active is not None:
                thread.is_active = is_active
            if discussion_id is not None:
                thread.discussion_id = discussion_id
            if metadata is not None:
                thread.metadata_json = metadata

            await self.db_session.commit()
            await self.db_session.refresh(thread)

            logger.info(
                "Updated thread",
                extra={
                    "thread_id": str(thread_id),
                    "user_id": str(thread.user_id),
                },
            )

            return thread

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error updating thread %s: %s", thread_id, str(e))
            raise

    async def delete_thread(
        self,
        thread_id: uuid.UUID,
        archive: bool = True,
    ) -> bool:
        """
        Delete or archive a conversation thread.

        Args:
            thread_id: UUID of the thread to delete
            archive: If True, archive instead of deleting

        Returns:
            True if successful, False if not found
        """
        try:
            thread = await self.get_thread(thread_id)

            if not thread:
                logger.warning("Thread not found or not accessible: %s", thread_id)
                return False

            if archive:
                thread.is_active = False
                thread.archived_at = datetime.now(tz=UTC)
                await self.db_session.commit()
            else:
                await self.db_session.delete(thread)
                await self.db_session.commit()

            logger.info(
                "Deleted thread",
                extra={
                    "thread_id": str(thread_id),
                    "archived": archive,
                },
            )

            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error deleting thread %s: %s", thread_id, str(e))
            raise

    async def get_thread_messages(
        self,
        thread_id: uuid.UUID,
    ) -> list[ThreadMessage]:
        """
        Get all messages in a thread, ordered by sequence.

        Args:
            thread_id: UUID of the thread (using thread.id, not thread.thread_id)

        Returns:
            List of thread messages
        """
        try:
            stmt = (
                select(ThreadMessage)
                .where(ThreadMessage.thread_id == thread_id)
                .order_by(ThreadMessage.sequence_number)
            )
            result = await self.db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error("Error retrieving thread messages %s: %s", thread_id, str(e))
            raise

    async def add_thread_message(
        self,
        thread_id: uuid.UUID,
        query_id: uuid.UUID | None,
        role: str,
        content: str,
        token_count: int,
        model_used: str | None = None,
    ) -> ThreadMessage:
        """
        Add a new message to a thread.

        Args:
            thread_id: UUID of the thread (using thread.id, not thread.thread_id)
            query_id: Optional UUID of associated query
            role: Message role (user, assistant, system)
            content: Message content
            token_count: Number of tokens in the message
            model_used: Optional model identifier

        Returns:
            The created thread message
        """
        try:
            # Get current max sequence number
            max_seq_stmt = select(func.max(ThreadMessage.sequence_number)).where(
                ThreadMessage.thread_id == thread_id
            )
            max_seq_result = await self.db_session.execute(max_seq_stmt)
            max_seq = max_seq_result.scalar() or 0

            message = ThreadMessage(
                thread_id=thread_id,
                query_id=query_id,
                sequence_number=max_seq + 1,
                role=role,
                content=content,
                token_count=token_count,
                model_used=model_used,
            )

            self.db_session.add(message)

            # Update thread metadata
            thread_stmt = select(ContextThread).where(ContextThread.id == thread_id)
            thread_result = await self.db_session.execute(thread_stmt)
            thread = thread_result.scalar_one_or_none()

            if thread:
                thread.message_count += 1
                thread.last_activity_at = datetime.now(tz=UTC)
                thread.context_size_tokens += token_count

            await self.db_session.commit()
            await self.db_session.refresh(message)

            logger.info(
                "Added thread message",
                extra={
                    "thread_id": str(thread_id),
                    "role": role,
                    "sequence": max_seq + 1,
                },
            )

            return message

        except Exception as e:
            await self.db_session.rollback()
            logger.error("Error adding thread message: %s", str(e))
            raise

    async def find_or_create_thread(
        self,
        user_id: uuid.UUID,
        discussion_id: str | None,
        use_case_id: uuid.UUID | None,
        source: str = "api",
    ) -> ContextThread:
        """
        Find an active thread or create a new one.
        Used for SOAR API calls with discussion_id.

        Args:
            user_id: UUID of the user
            discussion_id: Optional discussion/incident ID
            use_case_id: Optional use case UUID
            source: Source of the request (api, soar, etc.)

        Returns:
            Existing or newly created thread
        """
        try:
            # Try to find recent active thread with matching criteria
            if discussion_id and use_case_id:
                stmt = (
                    select(ContextThread)
                    .where(
                        and_(
                            ContextThread.user_id == user_id,
                            ContextThread.discussion_id == discussion_id,
                            ContextThread.use_case_id == use_case_id,
                            ContextThread.is_active.is_(True),
                        )
                    )
                    .order_by(desc(ContextThread.last_activity_at))
                    .limit(1)
                )
                result = await self.db_session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(
                        "Found existing thread",
                        extra={
                            "thread_id": str(existing.thread_id),
                            "discussion_id": discussion_id,
                        },
                    )
                    return existing

            # Create new thread
            title = f"Auto-created: {discussion_id or 'API Query'}"
            return await self.create_thread(
                user_id=user_id,
                title=title,
                discussion_id=discussion_id,
                use_case_id=use_case_id,
                source=source,
            )

        except Exception as e:
            logger.error("Error finding or creating thread: %s", str(e))
            raise
