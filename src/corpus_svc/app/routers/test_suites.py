"""
Test Suite API endpoints for corpus validation.

Provides CRUD operations and execution for test suites with retrieval metrics.
Part of Layer 3: Corpus Management Backend (P4-F10)
ADR-034: Use Case Validation & Test Harness
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import get_logger

from ..db.connection import get_db_session
from ..schemas.test_suite import (
    TestQuestion,
    TestQuestionCreate,
    TestSuite,
    TestSuiteCreate,
    TestSuiteExecutionRequest,
    TestSuiteExecutionResponse,
    TestSuiteResult,
    TestSuiteUpdate,
)
from ..services.test_suite_service import TestSuiteService

logger = get_logger(__name__)

router = APIRouter(
    prefix="",  # Prefix added by main.py api_router
    tags=["test-suites"],
    responses={404: {"description": "Not found"}},
)


def get_test_suite_service(
    db: AsyncSession = Depends(get_db_session),
) -> TestSuiteService:
    """Dependency to get TestSuiteService instance."""
    return TestSuiteService(db)


@router.post("", response_model=TestSuite, status_code=status.HTTP_201_CREATED)
async def create_test_suite(
    test_suite: TestSuiteCreate,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> TestSuite:
    """
    Create a new test suite with questions.

    Args:
        test_suite: Test suite creation data
        service: TestSuiteService dependency

    Returns:
        Created test suite
    """
    try:
        created = await service.create_test_suite(test_suite)
        logger.info(f"Created test suite: {created.id}")
        return created
    except Exception as e:
        logger.error(f"Failed to create test suite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test suite: {e!s}",
        ) from e


@router.get("", response_model=list[TestSuite])
async def list_test_suites(
    limit: int = 100,
    offset: int = 0,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> list[TestSuite]:
    """
    List all test suites with pagination.

    Args:
        limit: Maximum number to return (default 100)
        offset: Number to skip (default 0)
        service: TestSuiteService dependency

    Returns:
        List of test suites
    """
    try:
        return await service.list_test_suites(limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Failed to list test suites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list test suites: {e!s}",
        ) from e


@router.get("/{suite_id}", response_model=TestSuite)
async def get_test_suite(
    suite_id: UUID,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> TestSuite:
    """
    Get a test suite by ID.

    Args:
        suite_id: Test suite UUID
        service: TestSuiteService dependency

    Returns:
        Test suite

    Raises:
        HTTPException: 404 if not found
    """
    suite = await service.get_test_suite(suite_id)
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite {suite_id} not found",
        )
    return suite


@router.patch("/{suite_id}", response_model=TestSuite)
async def update_test_suite(
    suite_id: UUID,
    test_suite_update: TestSuiteUpdate,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> TestSuite:
    """
    Update a test suite.

    Args:
        suite_id: Test suite UUID
        test_suite_update: Update data
        service: TestSuiteService dependency

    Returns:
        Updated test suite

    Raises:
        HTTPException: 404 if not found
    """
    updated = await service.update_test_suite(suite_id, test_suite_update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite {suite_id} not found",
        )
    logger.info(f"Updated test suite: {suite_id}")
    return updated


@router.delete("/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_suite(
    suite_id: UUID,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> None:
    """
    Delete a test suite.

    Args:
        suite_id: Test suite UUID
        service: TestSuiteService dependency

    Raises:
        HTTPException: 404 if not found
    """
    deleted = await service.delete_test_suite(suite_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite {suite_id} not found",
        )
    logger.info(f"Deleted test suite: {suite_id}")


@router.post(
    "/{suite_id}/questions",
    response_model=TestQuestion,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    suite_id: UUID,
    question: TestQuestionCreate,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> TestQuestion:
    """
    Add a question to an existing test suite.

    Args:
        suite_id: Test suite UUID
        question: Question creation data
        service: TestSuiteService dependency

    Returns:
        Created question

    Raises:
        HTTPException: 404 if suite not found
    """
    created_question = await service.add_question(suite_id, question)
    if not created_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite {suite_id} not found",
        )
    logger.info(f"Added question to suite {suite_id}")
    return created_question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: UUID,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> None:
    """
    Delete a test question.

    Args:
        question_id: Question UUID
        service: TestSuiteService dependency

    Raises:
        HTTPException: 404 if not found
    """
    deleted = await service.delete_question(question_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {question_id} not found",
        )
    logger.info(f"Deleted question: {question_id}")


@router.post("/{suite_id}/execute", response_model=TestSuiteExecutionResponse)
async def execute_test_suite(
    suite_id: UUID,
    execution_request: TestSuiteExecutionRequest,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> TestSuiteExecutionResponse:
    """
    Execute a test suite and compute retrieval metrics.

    TODO: Implement actual execution logic with retrieval service integration.
    This endpoint is a placeholder that will be completed when retrieval
    integration is ready.

    Args:
        suite_id: Test suite UUID
        execution_request: Execution parameters
        service: TestSuiteService dependency

    Returns:
        Execution results with metrics

    Raises:
        HTTPException: 404 if suite not found, 501 if not implemented
    """
    # Verify suite exists
    suite = await service.get_test_suite(suite_id)
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite {suite_id} not found",
        )

    # TODO: Implement actual execution
    # This requires:
    # 1. Retrieval service integration
    # 2. Per-query execution with metrics collection
    # 3. Aggregation of results
    # 4. Saving results to database

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Test suite execution not yet implemented. Requires retrieval service integration.",
    )


@router.get("/{suite_id}/results", response_model=list[TestSuiteResult])
async def get_suite_results(
    suite_id: UUID,
    limit: int = 20,
    service: TestSuiteService = Depends(get_test_suite_service),
) -> list[TestSuiteResult]:
    """
    Get execution results for a test suite.

    Args:
        suite_id: Test suite UUID
        limit: Maximum number of results to return
        service: TestSuiteService dependency

    Returns:
        List of execution results (newest first)
    """
    return await service.get_suite_results(suite_id, limit=limit)
