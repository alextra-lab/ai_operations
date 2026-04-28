"""
Stateless architecture endpoints (ADR-030, ADR-031).

Provides export and summary generation from client-provided conversation data
without server-side storage.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..schemas.run_manifest import ExportRequest, ExportResponse
from ..schemas.summaries import ConversationMessage, SummaryRequest, SummaryResponse
from ..services.export_service import ExportService
from ..services.summary_service import SummaryService

# Configure logger for this module
logger = configure_logging(service_name="stateless_router")

router = APIRouter(prefix="/api/v1/stateless", tags=["stateless"])


@router.post("/export", response_model=ExportResponse)
async def export_conversation(
    request: ExportRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> ExportResponse:
    """
    Export conversation from client-provided data.

    This endpoint generates exports on-demand from client data without
    storing content server-side (ADR-031).

    Args:
        request: Export request with conversation data
        current_user: Current authenticated user

    Returns:
        Export response with content or download URL

    Raises:
        HTTPException: If export generation fails
    """
    try:
        logger.info(
            "Generating conversation export",
            extra={
                "user_id": str(current_user.user_id),
                "conversation_id": request.conversation_id,
                "format": request.format,
                "message_count": len(request.messages),
            },
        )

        export_service = ExportService()

        # Generate export based on format
        if request.format == "json":
            content = export_service.generate_json_export(
                conversation_id=request.conversation_id,
                export_timestamp=request.export_timestamp,
                use_case=request.use_case,
                messages=request.messages,
                session_metadata=request.session_metadata,
            )
        elif request.format == "markdown":
            content = export_service.generate_markdown_export(
                conversation_id=request.conversation_id,
                export_timestamp=request.export_timestamp,
                use_case=request.use_case,
                messages=request.messages,
                session_metadata=request.session_metadata,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}",
            )

        # Generate export ID
        export_id = export_service.generate_export_id(
            conversation_id=request.conversation_id,
            timestamp=request.export_timestamp,
        )

        logger.info(
            "Export generated successfully",
            extra={
                "user_id": str(current_user.user_id),
                "export_id": export_id,
                "format": request.format,
            },
        )

        return ExportResponse(
            export_id=export_id,
            format=request.format,
            content=content,
            download_url=None,  # v1 returns content directly
        )

    except Exception as e:
        logger.error(
            "Error generating export",
            extra={
                "user_id": str(current_user.user_id),
                "conversation_id": request.conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate export",
        ) from e


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> SummaryResponse:
    """
    Generate summary from client-provided conversation data.

    This endpoint generates summaries on-demand from client data without
    storing content server-side (ADR-031).

    Args:
        request: Summary request with message data
        current_user: Current authenticated user

    Returns:
        Summary response with generated content

    Raises:
        HTTPException: If summary generation fails
    """
    try:
        logger.info(
            "Generating conversation summary",
            extra={
                "user_id": str(current_user.user_id),
                "export_format": request.export_format,
                "message_count": len(request.messages),
            },
        )

        summary_service = SummaryService()

        # Convert dict messages to ConversationMessage objects if needed
        conversation_messages: list[ConversationMessage] = []
        for msg in request.messages:
            if isinstance(msg, dict):
                conversation_messages.append(ConversationMessage(**msg))
            else:
                conversation_messages.append(msg)

        # Generate summary
        result = await summary_service.generate(
            use_case_id=request.use_case_id,
            messages=conversation_messages,
            export_format=request.export_format,
            redaction=request.redaction,
        )

        logger.info(
            "Summary generated successfully",
            extra={
                "user_id": str(current_user.user_id),
                "export_format": request.export_format,
                "message_count": result.message_count,
            },
        )

        # result is already a SummaryResponse
        return result

    except Exception as e:
        logger.error(
            "Error generating summary",
            extra={
                "user_id": str(current_user.user_id),
                "export_format": request.export_format,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary",
        ) from e
