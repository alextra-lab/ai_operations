"""
Tool registration API endpoints.

Provides multi-phase guided workflow for MCP tool registration.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)

from ..db.database import get_async_db
from ..schemas.tool_registration import (
    RegistrationSessionResponse,
    ToolRegistrationPhase,
    ToolRegistrationRequest,
    ToolRegistrationResponse,
)
from ..services.tool_registration_service import ToolRegistrationService

router = APIRouter(prefix="/api/v1/admin/tools/register", tags=["admin", "tools", "registration"])


@router.post("", response_model=ToolRegistrationResponse)
async def register_tool_phase(
    request: ToolRegistrationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ToolRegistrationResponse:
    """
    Process a registration workflow phase.

    Multi-phase registration workflow:
    1. basic_info - Tool identification and categorization
    2. mcp_config - MCP server connection details
    3. security_config - Authentication and secrets
    4. connection_test - Test connection and discover capabilities (uses credentials from step 3)
    5. permissions - RBAC permissions and rate limits
    6. review - Review complete configuration
    7. commit - Atomic registration commit

    **Requires:** admin role
    """
    registration_service = ToolRegistrationService(db)
    user_id = UUID(current_user.user_id)

    try:
        session, result = await registration_service.process_phase(
            session_id=request.session_id,
            phase=request.phase,
            data=request.data,
            user_id=user_id,
        )

        # Build response
        return ToolRegistrationResponse(
            session_id=session.session_id,
            current_phase=session.current_phase,
            next_phase=(
                registration_service._get_next_phase(session.current_phase)
                if result.get("success") and session.can_proceed
                else None
            ),
            validation_errors=session.validation_errors,
            can_proceed=session.can_proceed,
            discovered_capabilities=(
                session.connection_result
                if request.phase == ToolRegistrationPhase.CONNECTION_TEST
                and session.connection_result
                else None
            ),
            tool_id=result.get("tool_id"),
            message=result.get("message", "Phase processed successfully"),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Registration phase error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {e!s}",
        ) from e


@router.get("/session/{session_id}", response_model=RegistrationSessionResponse)
async def get_registration_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> RegistrationSessionResponse:
    """
    Retrieve registration session state.

    Useful for resuming interrupted registrations or debugging.

    **Requires:** admin role
    """
    registration_service = ToolRegistrationService(db)

    try:
        session = registration_service.get_session_state(session_id)

        # Build collected data
        collected_data = {}
        if session.basic_info:
            collected_data["basic_info"] = session.basic_info
        if session.mcp_config:
            collected_data["mcp_config"] = session.mcp_config
        if session.connection_result:
            collected_data["connection_result"] = session.connection_result
        if session.security_config:
            # Mask secret value
            security_config = session.security_config.copy()
            if "secret_value" in security_config:
                security_config["secret_value"] = "***REDACTED***"
            collected_data["security_config"] = security_config
        if session.permissions_config:
            collected_data["permissions_config"] = session.permissions_config

        # Build validation status
        validation_status = {
            phase.value: phase.value not in session.validation_errors
            for phase in ToolRegistrationPhase
        }

        return RegistrationSessionResponse(
            session_id=session.session_id,
            current_phase=session.current_phase,
            created_at=session.created_at,
            updated_at=session.updated_at,
            expires_at=session.expires_at,
            collected_data=collected_data,
            validation_status=validation_status,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_registration(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> None:
    """
    Cancel registration and cleanup session.

    **Requires:** admin role
    """
    registration_service = ToolRegistrationService(db)

    try:
        registration_service.cancel_registration(session_id)
    except Exception as e:
        logger.warning(f"Failed to cancel session {session_id}: {e}")
        # Don't raise error - session may already be cleaned up
