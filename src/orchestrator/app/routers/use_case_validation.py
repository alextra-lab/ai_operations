"""
Use Case validation API endpoints.

Provides endpoints for validating Use Case configurations and applying auto-fixes.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TokenPayload, get_current_user
from shared.config.schemas import OrchestratorConfig
from shared.logging_utils.fastapi import get_logger

from ..config.runtime import build_runtime_config
from ..db.database import get_async_db
from ..db.models import UseCase as DBUseCase
from ..dependencies.config import get_orchestrator_settings
from ..orchestrator.controller import Orchestrator
from ..services.use_case_testing_service import (
    TestCase,
    TestQueryResult,
    TestSuiteResult,
    UseCaseTestingService,
)
from ..services.validation import ValidationEngine, ValidationReport

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/use-cases", tags=["use-cases", "validation"])
bearer_scheme = HTTPBearer()


class AutoFixRequest(BaseModel):
    """Request to auto-fix validation issues."""

    issue_ids: list[str] = Field(..., description="List of rule IDs to auto-fix")


class TestQueryRequest(BaseModel):
    """Request to execute a test query."""

    query: str = Field(..., description="Test query text")
    expected_output: dict[str, Any] | None = Field(
        None, description="Expected output for validation"
    )


class TestSuiteRequest(BaseModel):
    """Request to run a test suite."""

    test_cases: list[TestCase] = Field(..., description="List of test cases")


def deep_merge(target: dict, source: dict) -> dict:
    """
    Deep merge source dict into target dict.

    Args:
        target: Target dictionary
        source: Source dictionary to merge

    Returns:
        Merged dictionary
    """
    result = target.copy()
    for key, value in source.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@router.post("/{use_case_id}/validate", response_model=ValidationReport)
async def validate_use_case(
    use_case_id: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ValidationReport:
    """
    Validate Use Case configuration and prompts.

    Returns validation report with errors, warnings, and suggestions.

    Args:
        use_case_id: Use Case ID to validate
        current_user: Current authenticated user
        db: Async database session

    Returns:
        ValidationReport with all issues grouped by severity

    Raises:
        HTTPException: 404 if Use Case not found
    """
    # Load Use Case from database
    stmt = select(DBUseCase).where(DBUseCase.use_case_id == use_case_id)
    result = await db.execute(stmt)
    use_case = result.scalar_one_or_none()
    if not use_case:
        raise HTTPException(status_code=404, detail="Use Case not found")

    # Convert to dict for validation
    use_case_dict = {
        "use_case_id": use_case.use_case_id,
        "config_json": use_case.config_json or {},
        "metadata_json": use_case.metadata_json or {},
    }

    # Run validation
    engine = ValidationEngine()
    report = engine.validate_use_case(
        use_case=use_case_dict,
        _context={
            "user_role": current_user.roles[0] if current_user.roles else "user",
            "username": current_user.sub,
        },
    )

    logger.info(
        f"Validation completed for Use Case {use_case_id} by {current_user.sub}: "
        f"{len(report.errors)} errors, {len(report.warnings)} warnings, "
        f"{len(report.infos)} suggestions"
    )

    return report


@router.post("/{use_case_id}/auto-fix")
async def auto_fix_issues(
    use_case_id: str,
    request: AutoFixRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Auto-fix validation issues where possible.

    Requires corpus_admin or admin role.

    Args:
        use_case_id: Use Case ID
        request: Auto-fix request with issue IDs
        current_user: Current authenticated user (must be admin)
        db: Async database session

    Returns:
        Updated Use Case with fixes applied

    Raises:
        HTTPException: 403 if unauthorized, 404 if Use Case not found, 400 if no fixable issues
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    # Load Use Case from database
    stmt = select(DBUseCase).where(DBUseCase.use_case_id == use_case_id)
    result = await db.execute(stmt)
    use_case = result.scalar_one_or_none()
    if not use_case:
        raise HTTPException(status_code=404, detail="Use Case not found")

    # Convert to dict for validation
    use_case_dict = {
        "use_case_id": use_case.use_case_id,
        "config_json": use_case.config_json or {},
        "metadata_json": use_case.metadata_json or {},
    }

    # Get validation issues
    engine = ValidationEngine()
    report = engine.validate_use_case(use_case_dict)

    # Filter to requested issues with auto-fix
    to_fix = [i for i in report.issues if i.rule_id in request.issue_ids and i.auto_fix]

    if not to_fix:
        raise HTTPException(status_code=400, detail="No auto-fixable issues found")

    # Apply fixes to config_json
    if use_case.config_json is None:
        raise HTTPException(
            status_code=400, detail="Use Case config_json is None, cannot apply fixes"
        )
    updated_config = use_case.config_json.copy()
    for issue in to_fix:
        logger.info(
            f"Applying auto-fix for rule {issue.rule_id} in Use Case {use_case_id} "
            f"by {current_user.sub}"
        )
        # Deep merge auto_fix into config
        if issue.auto_fix:
            updated_config = deep_merge(updated_config, issue.auto_fix)

    # Update Use Case in database
    use_case.config_json = updated_config
    await db.commit()
    await db.refresh(use_case)

    logger.info(
        f"Auto-fixed {len(to_fix)} issue(s) in Use Case {use_case_id} by {current_user.sub}"
    )

    return {
        "success": True,
        "use_case_id": use_case_id,
        "fixed_issues": len(to_fix),
        "fixed_rule_ids": [i.rule_id for i in to_fix],
        "config_json": use_case.config_json,
    }


@router.post("/{use_case_id}/test", response_model=TestQueryResult)
async def test_use_case_query(
    use_case_id: str,
    request: TestQueryRequest,
    current_user: TokenPayload = Depends(get_current_user),
    raw_token_creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db),
    settings: OrchestratorConfig = Depends(get_orchestrator_settings),
) -> TestQueryResult:
    """
    Execute a test query against Use Case.

    Args:
        use_case_id: Use Case ID to test
        request: Test query request
        current_user: Current authenticated user
        raw_token_creds: Raw JWT token credentials
        db: Database session

    Returns:
        Test query result with execution details and validation
    """
    # Initialize orchestrator with config
    runtime_config = build_runtime_config(settings)

    # Extract user's JWT token for Gateway authentication
    raw_token = raw_token_creds.credentials if raw_token_creds else None

    # Create LLMRouter with JWT token for Inference Gateway
    from ..orchestrator.llm_router import LLMRouter

    if raw_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT token")

    llm_router = LLMRouter(
        user_jwt_token=raw_token,
        gateway_url=settings.inference_gateway_url,
        request_timeout_seconds=settings.request_timeout_seconds,
    )
    # All services now use async_db
    orchestrator = Orchestrator(async_db=db, config=runtime_config, llm_router=llm_router)
    testing_service = UseCaseTestingService(orchestrator)

    return await testing_service.execute_test_query(
        use_case_id=use_case_id,
        test_query=request.query,
        expected_output=request.expected_output,
        user_id=current_user.sub,
    )


@router.post("/{use_case_id}/test-suite", response_model=TestSuiteResult)
async def run_use_case_test_suite(
    use_case_id: str,
    request: TestSuiteRequest,
    current_user: TokenPayload = Depends(get_current_user),
    raw_token_creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db),
    settings: OrchestratorConfig = Depends(get_orchestrator_settings),
) -> TestSuiteResult:
    """
    Run a test suite against Use Case.

    Args:
        use_case_id: Use Case ID to test
        request: Test suite request with test cases
        current_user: Current authenticated user
        raw_token_creds: Raw JWT token credentials
        db: Database session

    Returns:
        Test suite result with aggregated statistics
    """
    # Initialize orchestrator with config
    runtime_config = build_runtime_config(settings)

    # Extract user's JWT token for Gateway authentication
    raw_token = raw_token_creds.credentials if raw_token_creds else None

    # Create LLMRouter with JWT token for Inference Gateway
    from ..orchestrator.llm_router import LLMRouter

    if raw_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT token")

    llm_router = LLMRouter(
        user_jwt_token=raw_token,
        gateway_url=settings.inference_gateway_url,
        request_timeout_seconds=settings.request_timeout_seconds,
    )
    # All services now use async_db
    orchestrator = Orchestrator(async_db=db, config=runtime_config, llm_router=llm_router)
    testing_service = UseCaseTestingService(orchestrator)

    result = await testing_service.run_test_suite(
        use_case_id=use_case_id, test_cases=request.test_cases
    )

    logger.info(
        f"Test suite executed for {use_case_id} by {current_user.sub}: "
        f"{result.passed}/{result.total_tests} passed"
    )

    return result
