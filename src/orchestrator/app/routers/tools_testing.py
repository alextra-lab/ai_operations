"""
Tool testing API endpoints.

Provides endpoints for testing tool execution and validating parameters
before adding tools to use cases.
"""

import time
from typing import Any
from uuid import UUID

import jsonschema
from fastapi import APIRouter, Body, Depends, HTTPException, status
from jsonschema import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..db.models import Tool
from ..services.tool_executor import ToolExecutor

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tools/test", tags=["tools", "testing"])


def require_developer_or_admin(current_user: TokenPayload) -> None:
    """
    Verify current user is developer or admin.

    Raises:
        HTTPException: If user doesn't have permission
    """
    allowed_roles = ["admin", "developer"]
    if not current_user.has_any_role(allowed_roles):
        logger.warning(
            "Unauthorized tool testing access attempt",
            extra={"user_id": current_user.user_id, "roles": current_user.roles},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or developer roles can test tools",
        )


@router.post("/execute")
async def test_tool_execution(
    tool_id: UUID = Body(..., description="UUID of the tool to test"),
    tool_name: str = Body(..., description="Name of the specific tool to call"),
    parameters: dict[str, Any] = Body(..., description="Tool parameters dictionary"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Test tool execution with provided parameters.

    Executes a tool call for testing purposes. Test executions are audited
    but marked as test runs to distinguish from production usage.

    **Requires:** developer or admin role

    Args:
        tool_id: UUID of the tool to test
        tool_name: Name of the specific tool to call
        parameters: Tool parameters dictionary
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dictionary with test execution results:
        - success: Boolean indicating if execution succeeded
        - status: Status string ("success" or "error")
        - result: Tool execution result (if successful)
        - error: Error message (if failed)
        - duration_ms: Execution duration in milliseconds

    Raises:
        HTTPException: If user lacks permission or tool not found
    """
    # Check permissions
    require_developer_or_admin(current_user)

    # Verify tool exists
    stmt = select(Tool).where(Tool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if not tool:
        logger.warning(
            "Tool not found for testing",
            extra={"tool_id": str(tool_id), "user_id": current_user.user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )

    # Check if tool is enabled
    if not tool.is_enabled:
        logger.warning(
            "Attempted to test disabled tool",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool.tool_id,
                "user_id": current_user.user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool {tool.tool_id} is disabled",
        )

    executor = ToolExecutor(db)
    start_time = time.time()

    try:
        logger.info(
            "Testing tool execution",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "user_id": current_user.user_id,
                "user_role": current_user.roles[0] if current_user.roles else "user",
            },
        )

        exec_result = await executor.execute_tool(
            tool_id=tool_id,
            tool_name=tool_name,
            parameters=parameters,
            user_id=UUID(current_user.user_id),
            user_roles=(
                current_user.roles if current_user.roles else ["user"]
            ),  # Multi-role support per ADR-060
            run_id=f"test_{current_user.user_id}",
        )

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Tool test execution succeeded",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "user_id": current_user.user_id,
            },
        )

        return {
            "success": True,
            "status": "success",
            "result": exec_result,
            "duration_ms": round(duration_ms, 2),
        }

    except ValueError as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.warning(
            "Tool test execution failed - validation error",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "error": error_msg,
                "duration_ms": duration_ms,
                "user_id": current_user.user_id,
            },
        )

        return {
            "success": False,
            "status": "error",
            "error": error_msg,
            "duration_ms": round(duration_ms, 2),
        }

    except RuntimeError as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.warning(
            "Tool test execution failed - runtime error",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "error": error_msg,
                "duration_ms": duration_ms,
                "user_id": current_user.user_id,
            },
        )

        return {
            "success": False,
            "status": "error",
            "error": error_msg,
            "duration_ms": round(duration_ms, 2),
        }

    except PermissionError as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.warning(
            "Tool test execution failed - permission error",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "error": error_msg,
                "duration_ms": duration_ms,
                "user_id": current_user.user_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.error(
            "Tool test execution failed - unexpected error",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "error": error_msg,
                "duration_ms": duration_ms,
                "user_id": current_user.user_id,
            },
            exc_info=True,
        )

        return {
            "success": False,
            "status": "error",
            "error": f"Tool execution failed: {error_msg}",
            "duration_ms": round(duration_ms, 2),
        }


@router.post("/validate-parameters")
async def validate_tool_parameters(
    tool_id: UUID = Body(..., description="UUID of the tool to validate"),
    parameters: dict[str, Any] = Body(..., description="Tool parameters to validate"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Validate tool parameters against schema without executing.

    Validates the provided parameters against the tool's JSON schema
    without actually executing the tool. Useful for pre-flight validation
    before adding tools to use cases.

    **Requires:** developer or admin role

    Args:
        tool_id: UUID of the tool to validate
        parameters: Tool parameters dictionary to validate
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dictionary with validation results:
        - valid: Boolean indicating if parameters are valid
        - message: Optional message (if no schema defined)
        - error: Optional error message (if validation failed)

    Raises:
        HTTPException: If user lacks permission or tool not found
    """
    # Check permissions
    require_developer_or_admin(current_user)

    # Verify tool exists
    stmt = select(Tool).where(Tool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if not tool:
        logger.warning(
            "Tool not found for parameter validation",
            extra={"tool_id": str(tool_id), "user_id": current_user.user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )

    # Check if schema is defined
    schema = tool.parameters_schema
    if not schema:
        logger.info(
            "Tool has no parameter schema defined",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool.tool_id,
                "user_id": current_user.user_id,
            },
        )
        return {"valid": True, "message": "No schema defined"}

    # Validate against JSON schema
    try:
        jsonschema.validate(instance=parameters, schema=schema)
        logger.info(
            "Tool parameters validated successfully",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool.tool_id,
                "user_id": current_user.user_id,
            },
        )
        return {"valid": True}

    except ValidationError as e:
        error_msg = e.message
        logger.warning(
            "Tool parameter validation failed",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool.tool_id,
                "error": error_msg,
                "user_id": current_user.user_id,
            },
        )
        return {"valid": False, "error": error_msg}

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Tool parameter validation failed - unexpected error",
            extra={
                "tool_id": str(tool_id),
                "tool_name": tool.tool_id,
                "error": error_msg,
                "user_id": current_user.user_id,
            },
            exc_info=True,
        )
        return {"valid": False, "error": f"Validation error: {error_msg}"}
