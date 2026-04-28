"""
Test Suite Service for corpus validation.

Manages test suites, questions, and execution for retrieval quality metrics.
ADR-034: Use Case Validation & Test Harness

Fully async per ADR-022 (P5-A23 - converted Nov 2025).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import get_logger

from ..schemas.suite_testing import (
    TestQuestion,
    TestQuestionCreate,
    TestSuite,
    TestSuiteCreate,
    TestSuiteResult,
    TestSuiteResultCreate,
    TestSuiteUpdate,
)

logger = get_logger(__name__)


class TestSuiteService:
    """Service for managing test suites and execution."""

    def __init__(self, db_session: AsyncSession):
        """Initialize service with async database session."""
        self.db = db_session

    async def create_test_suite(
        self,
        test_suite_create: TestSuiteCreate,
        created_by: UUID | None = None,
    ) -> TestSuite:
        """
        Create a new test suite with questions.

        Args:
            test_suite_create: Test suite creation data
            created_by: User ID who created the suite

        Returns:
            Created test suite with questions
        """
        # Insert test suite
        insert_suite_query = text(
            """
        INSERT INTO corpus_test_suites (name, description, collection_ids, k, created_by)
        VALUES (:name, :description, :collection_ids, :k, :created_by)
        RETURNING id, name, description, collection_ids, k, created_at, updated_at, created_by
        """
        )

        suite_result = await self.db.execute(
            insert_suite_query,
            {
                "name": test_suite_create.name,
                "description": test_suite_create.description,
                "collection_ids": [str(cid) for cid in test_suite_create.collection_ids],
                "k": test_suite_create.k,
                "created_by": str(created_by) if created_by else None,
            },
        )

        suite_row = suite_result.fetchone()

        if not suite_row:
            raise ValueError("Failed to create test suite")

        suite_id = suite_row.id

        # Insert questions if provided
        questions = []
        if test_suite_create.questions:
            for question_data in test_suite_create.questions:
                # Convert TestQuestionBase to TestQuestionCreate by adding suite_id
                question_create = TestQuestionCreate(
                    suite_id=suite_id, **question_data.model_dump()
                )
                question = await self._create_question(suite_id, question_create)
                questions.append(question)

        # Commit the transaction
        await self.db.commit()

        # Fetch complete suite
        test_suite = await self.get_test_suite(suite_id)

        if not test_suite:
            raise ValueError(f"Failed to fetch created test suite {suite_id}")

        logger.info(
            f"Created test suite {suite_id} with {len(questions)} questions",
            extra={"suite_id": str(suite_id), "question_count": len(questions)},
        )

        return test_suite

    async def _create_question(
        self, suite_id: UUID, question_data: TestQuestionCreate
    ) -> TestQuestion:
        """Create a single test question."""
        insert_question_query = text(
            """
        INSERT INTO corpus_test_questions (
            suite_id, query, expected_doc_ids, expected_phrases, tags, relevance_scores
        )
        VALUES (
            :suite_id, :query, :expected_doc_ids, :expected_phrases, :tags, :relevance_scores
        )
        RETURNING id, suite_id, query, expected_doc_ids, expected_phrases, tags, relevance_scores, created_at
        """
        )

        result = await self.db.execute(
            insert_question_query,
            {
                "suite_id": str(suite_id),
                "query": question_data.query,
                "expected_doc_ids": [str(did) for did in question_data.expected_doc_ids],
                "expected_phrases": question_data.expected_phrases,
                "tags": question_data.tags,
                "relevance_scores": question_data.relevance_scores,
            },
        )

        row = result.fetchone()

        return TestQuestion.model_validate(row)

    async def get_test_suite(self, suite_id: UUID) -> TestSuite | None:
        """
        Get test suite by ID with all questions.

        Args:
            suite_id: Test suite UUID

        Returns:
            Test suite or None if not found
        """
        # Fetch suite
        suite_query = text(
            """
        SELECT id, name, description, collection_ids, k, created_at, updated_at, created_by
        FROM corpus_test_suites
        WHERE id = :suite_id
        """
        )

        suite_result = await self.db.execute(suite_query, {"suite_id": str(suite_id)})
        suite_row = suite_result.fetchone()

        if not suite_row:
            return None

        # Fetch questions
        questions_query = text(
            """
        SELECT id, suite_id, query, expected_doc_ids, expected_phrases, tags, relevance_scores, created_at
        FROM corpus_test_questions
        WHERE suite_id = :suite_id
        ORDER BY created_at
        """
        )

        questions_result = await self.db.execute(questions_query, {"suite_id": str(suite_id)})
        question_rows = questions_result.fetchall()

        questions = [TestQuestion.model_validate(row) for row in question_rows]

        # Construct test suite
        test_suite_dict = dict(suite_row._mapping)
        test_suite_dict["questions"] = questions

        return TestSuite.model_validate(test_suite_dict)

    async def list_test_suites(self, limit: int = 100, offset: int = 0) -> list[TestSuite]:
        """
        List all test suites.

        Args:
            limit: Maximum number of suites to return
            offset: Number of suites to skip

        Returns:
            List of test suites
        """
        query = text(
            """
        SELECT id, name, description, collection_ids, k, created_at, updated_at, created_by
        FROM corpus_test_suites
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        )

        result = await self.db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()

        # Fetch questions for each suite
        suites = []
        for row in rows:
            suite_id = row.id
            questions = await self._get_suite_questions(suite_id)

            suite_dict = dict(row._mapping)
            suite_dict["questions"] = questions

            suites.append(TestSuite.model_validate(suite_dict))

        return suites

    async def _get_suite_questions(self, suite_id: UUID) -> list[TestQuestion]:
        """Get all questions for a test suite."""
        query = text(
            """
        SELECT id, suite_id, query, expected_doc_ids, expected_phrases, tags, relevance_scores, created_at
        FROM corpus_test_questions
        WHERE suite_id = :suite_id
        ORDER BY created_at
        """
        )

        result = await self.db.execute(query, {"suite_id": str(suite_id)})
        rows = result.fetchall()

        return [TestQuestion.model_validate(row) for row in rows]

    async def update_test_suite(
        self, suite_id: UUID, test_suite_update: TestSuiteUpdate
    ) -> TestSuite | None:
        """
        Update test suite.

        Args:
            suite_id: Test suite UUID
            test_suite_update: Update data

        Returns:
            Updated test suite or None if not found
        """
        from typing import Any

        # Build update query dynamically based on provided fields
        update_fields = []
        params: dict[str, Any] = {"suite_id": str(suite_id)}

        if test_suite_update.name is not None:
            update_fields.append("name = :name")
            params["name"] = test_suite_update.name

        if test_suite_update.description is not None:
            update_fields.append("description = :description")
            params["description"] = test_suite_update.description

        if test_suite_update.collection_ids is not None:
            update_fields.append("collection_ids = :collection_ids")
            params["collection_ids"] = [str(cid) for cid in test_suite_update.collection_ids]

        if test_suite_update.k is not None:
            update_fields.append("k = :k")
            params["k"] = test_suite_update.k

        if not update_fields:
            # No fields to update, just return current suite
            return await self.get_test_suite(suite_id)

        # Add updated_at
        update_fields.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now(tz=UTC)

        query_str = f"""
        UPDATE corpus_test_suites
        SET {", ".join(update_fields)}
        WHERE id = :suite_id
        RETURNING id
        """

        result = await self.db.execute(text(query_str), params)
        row = result.fetchone()

        if not row:
            return None

        await self.db.commit()

        return await self.get_test_suite(suite_id)

    async def delete_test_suite(self, suite_id: UUID) -> bool:
        """
        Delete test suite and all questions (CASCADE).

        Args:
            suite_id: Test suite UUID

        Returns:
            True if deleted, False if not found
        """
        query = text(
            """
        DELETE FROM corpus_test_suites
        WHERE id = :suite_id
        RETURNING id
        """
        )

        result = await self.db.execute(query, {"suite_id": str(suite_id)})
        row = result.fetchone()

        if row:
            await self.db.commit()
            logger.info(f"Deleted test suite {suite_id}")
            return True

        return False

    async def add_question(
        self, suite_id: UUID, question_data: TestQuestionCreate
    ) -> TestQuestion | None:
        """
        Add a question to an existing test suite.

        Args:
            suite_id: Test suite UUID
            question_data: Question creation data

        Returns:
            Created question or None if suite not found
        """
        # Verify suite exists
        suite = await self.get_test_suite(suite_id)
        if not suite:
            return None

        question = await self._create_question(suite_id, question_data)
        await self.db.commit()

        logger.info(f"Added question to suite {suite_id}")

        return question

    async def delete_question(self, question_id: UUID) -> bool:
        """
        Delete a test question.

        Args:
            question_id: Question UUID

        Returns:
            True if deleted, False if not found
        """
        query = text(
            """
        DELETE FROM corpus_test_questions
        WHERE id = :question_id
        RETURNING id
        """
        )

        result = await self.db.execute(query, {"question_id": str(question_id)})
        row = result.fetchone()

        if row:
            await self.db.commit()
            return True

        return False

    async def save_result(self, result_create: TestSuiteResultCreate) -> TestSuiteResult:
        """
        Save test suite execution result.

        Args:
            result_create: Result data

        Returns:
            Saved result
        """
        query = text(
            """
        INSERT INTO corpus_test_suite_results (
            suite_id, chunking_strategy, collection_id,
            avg_hit_at_k, avg_mrr, avg_ndcg, zero_result_rate,
            total_queries, execution_time_ms, metadata
        )
        VALUES (
            :suite_id, :chunking_strategy, :collection_id,
            :avg_hit_at_k, :avg_mrr, :avg_ndcg, :zero_result_rate,
            :total_queries, :execution_time_ms, :metadata
        )
        RETURNING id, suite_id, executed_at, chunking_strategy, collection_id,
                  avg_hit_at_k, avg_mrr, avg_ndcg, zero_result_rate,
                  total_queries, execution_time_ms, metadata
        """
        )

        result = await self.db.execute(
            query,
            {
                "suite_id": str(result_create.suite_id),
                "chunking_strategy": result_create.chunking_strategy,
                "collection_id": str(result_create.collection_id),
                "avg_hit_at_k": result_create.avg_hit_at_k,
                "avg_mrr": result_create.avg_mrr,
                "avg_ndcg": result_create.avg_ndcg,
                "zero_result_rate": result_create.zero_result_rate,
                "total_queries": result_create.total_queries,
                "execution_time_ms": result_create.execution_time_ms,
                "metadata": result_create.metadata,
            },
        )

        row = result.fetchone()
        await self.db.commit()

        test_suite_result = TestSuiteResult.model_validate(row)

        logger.info(
            f"Saved test suite result for suite {result_create.suite_id}",
            extra={
                "suite_id": str(result_create.suite_id),
                "avg_hit_at_k": result_create.avg_hit_at_k,
                "avg_mrr": result_create.avg_mrr,
            },
        )

        return test_suite_result

    async def get_suite_results(self, suite_id: UUID, limit: int = 20) -> list[TestSuiteResult]:
        """
        Get execution results for a test suite.

        Args:
            suite_id: Test suite UUID
            limit: Maximum number of results to return

        Returns:
            List of test suite results ordered by execution time (newest first)
        """
        query = text(
            """
        SELECT id, suite_id, executed_at, chunking_strategy, collection_id,
               avg_hit_at_k, avg_mrr, avg_ndcg, zero_result_rate,
               total_queries, execution_time_ms, metadata
        FROM corpus_test_suite_results
        WHERE suite_id = :suite_id
        ORDER BY executed_at DESC
        LIMIT :limit
        """
        )

        result = await self.db.execute(query, {"suite_id": str(suite_id), "limit": limit})
        rows = result.fetchall()

        return [TestSuiteResult.model_validate(row) for row in rows]
