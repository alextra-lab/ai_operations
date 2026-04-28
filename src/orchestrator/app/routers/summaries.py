"""
Summaries Router for Stateless Core v1

This module implements the summary generation API endpoint for creating
PII-free conversation summaries.

Follows ADR-031: Client-Owned Exports & Summary Generation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..schemas.summaries import SummaryRequest, SummaryResponse
from ..services.summary_service import SummaryService

logger = configure_logging(service_name="summaries_router", log_level="INFO", log_format="json")

router = APIRouter(prefix="/api/v1/summaries", tags=["summaries"])


@router.post("/", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    db: AsyncSession = Depends(get_async_db),
) -> SummaryResponse:
    """
    Generate a PII-free summary of a conversation.

    This endpoint accepts a conversation (messages array) and generates a
    concise, PII-free summary suitable for archival or sharing.

    Follows ADR-031: Client-Owned Exports
    - No conversation data is stored server-side
    - Summary is generated on-demand
    - Client owns the summary data

    Args:
        request: Summary generation request with messages
        db: Database session

    Returns:
        SummaryResponse with generated summary

    Raises:
        HTTPException: If summary generation fails
    """
    try:
        service = SummaryService(db)
        summary = await service.generate(
            use_case_id=request.use_case_id,
            messages=request.messages,
            export_format=request.export_format,
            redaction=request.redaction,
        )

        logger.info(
            "Summary generated: use_case_id=%s, message_count=%d, format=%s",
            request.use_case_id,
            len(request.messages),
            request.export_format,
        )

        return summary

    except ValueError as e:
        logger.error(f"Invalid summary request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail="Summary generation failed")


@router.post("/batch", response_model=list[SummaryResponse])
async def generate_summaries_batch(
    requests: list[SummaryRequest],
    db: AsyncSession = Depends(get_async_db),
) -> list[SummaryResponse]:
    """
    Generate summaries for multiple conversations (batch processing).

    Args:
        requests: List of summary generation requests
        db: Database session

    Returns:
        List of summary responses

    Raises:
        HTTPException: If batch processing fails
    """
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Batch size limited to 10 conversations")

    try:
        service = SummaryService(db)
        summaries = []

        for req in requests:
            summary = await service.generate(
                use_case_id=req.use_case_id,
                messages=req.messages,
                export_format=req.export_format,
                redaction=req.redaction,
            )
            summaries.append(summary)

        logger.info(f"Batch summary generation complete: {len(summaries)} summaries")

        return summaries

    except Exception as e:
        logger.error(f"Batch summary generation failed: {e}")
        raise HTTPException(status_code=500, detail="Batch summary generation failed")
