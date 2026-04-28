"""
Chunking Router for Stateless Core v1

This module implements the chunking API endpoints for document processing
in the corpus management enhancement.
"""

import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.connection import get_db_session
from ..schemas.chunking_enums import (
    ChunkingAnalysis,
    ChunkingConfig,
    ChunkingResult,
    ChunkingStrategy,
)
from ..schemas.preflight import PreflightReport
from ..services.chunking_service import ChunkingService
from ..services.preflight_service import PreflightAnalyzer

router = APIRouter(prefix="", tags=["chunking"])  # Prefix added by main.py api_router

# Global service instances
_chunking_service = ChunkingService()
_preflight_analyzer = PreflightAnalyzer(_chunking_service)


class PreflightAnalysisRequest(BaseModel):
    """Request for preflight analysis of document text."""

    text: str = Field(..., description="Document text to analyze")
    document_name: str | None = Field(None, description="Document filename")
    document_type: str | None = Field(None, description="MIME type")
    test_suite_id: UUID | None = Field(
        None, description="Optional test suite for retrieval metrics"
    )
    strategies: list[ChunkingStrategy] | None = Field(
        None, description="Specific strategies to test"
    )
    max_sample_tokens: int = Field(10000, description="Max tokens for sample analysis")


@router.post("/chunk", response_model=ChunkingResult)
async def chunk_document(
    text: str,
    config: ChunkingConfig,
    document_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ChunkingResult:
    """
    Chunk a document using the specified strategy.

    Args:
        text: The text content to chunk
        config: Chunking configuration
        document_id: Optional document identifier
        db: Database session

    Returns:
        Chunking result with chunks and metadata
    """
    return await _chunking_service.chunk_document(
        text=text,
        config=config,
        document_id=document_id,
    )


@router.post("/analyze", response_model=ChunkingAnalysis)
async def analyze_chunking_quality(
    result: ChunkingResult,
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ChunkingAnalysis:
    """
    Analyze the quality of a chunking result.

    Args:
        result: The chunking result to analyze
        document_id: Document identifier
        db: Database session

    Returns:
        Chunking analysis with quality metrics
    """
    return await _chunking_service.analyze_chunking_quality(
        result=result,
        document_id=document_id,
    )


@router.post("/preflight/analyze", response_model=PreflightReport)
async def preflight_analysis_file(
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
    test_suite_id: str | None = Form(None),
    strategies: str | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
) -> PreflightReport:
    """
    Preflight analysis with file upload.

    Accepts file upload, extracts text, and performs chunking strategy analysis.
    """
    # Read file content
    content_bytes = await file.read()
    file_name = file.filename or "unknown.txt"
    file_ext = file_name.split(".")[-1].lower() if "." in file_name else "txt"

    # Extract text based on file type
    extracted_text = None

    if file_ext == "pdf":
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                extracted_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to extract text from PDF: {e!s}"
            ) from e
    elif file_ext in ["txt", "md"]:
        extracted_text = content_bytes.decode("utf-8", errors="replace")
    elif file_ext in ["doc", "docx"]:
        raise HTTPException(
            status_code=400,
            detail="DOCX files not yet supported for preflight analysis.",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: PDF, TXT",
        )

    # Parse strategies if provided
    strategies_list = None
    if strategies:
        try:
            strategies_list = [ChunkingStrategy(s) for s in json.loads(strategies)]
        except (json.JSONDecodeError, TypeError, ValueError):
            strategies_list = None

    # Validate and convert test_suite_id to UUID
    test_suite_uuid = None
    if test_suite_id:
        try:
            test_suite_uuid = UUID(test_suite_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid test_suite_id format: '{test_suite_id}'. Must be a valid UUID.",
            )

    # Perform preflight analysis (ensure str for analyzer)
    return await _preflight_analyzer.analyze(
        text=extracted_text or "",
        document_name=file_name,
        document_type=file.content_type or "text/plain",
        document_size_bytes=len(content_bytes),
        test_suite_id=test_suite_uuid,
        strategies_to_test=strategies_list,
        max_sample_tokens=10000,
    )


@router.post("/preflight", response_model=PreflightReport)
async def preflight_analysis(
    request: PreflightAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
) -> PreflightReport:
    """
    Perform preflight analysis to recommend chunking strategy.

    Uses real PreflightAnalyzer to:
    - Analyze document structure (headings, tables, paragraphs)
    - Benchmark multiple chunking strategies
    - Generate confidence-based recommendation

    Args:
        request: Preflight analysis request
        db: Database session

    Returns:
        PreflightReport with structure analysis, strategy benchmarks, and recommendation
    """
    # Use real PreflightAnalyzer service
    return await _preflight_analyzer.analyze(
        text=request.text,
        document_name=request.document_name or "unnamed_document",
        document_type=request.document_type or "text/plain",
        document_size_bytes=len(request.text.encode("utf-8")),
        test_suite_id=request.test_suite_id,
        strategies_to_test=request.strategies if request.strategies else None,
        max_sample_tokens=request.max_sample_tokens or 10000,
    )


@router.get("/strategies", response_model=list[str])
async def get_available_strategies(
    db: AsyncSession = Depends(get_db_session),
) -> list[str]:
    """
    Get available chunking strategies.

    Args:
        db: Database session

    Returns:
        List of available chunking strategies
    """
    return [strategy.value for strategy in ChunkingStrategy]


@router.get("/strategies/{strategy}/config", response_model=ChunkingConfig)
async def get_strategy_config(
    strategy: ChunkingStrategy,
    db: AsyncSession = Depends(get_db_session),
) -> ChunkingConfig:
    """
    Get default configuration for a chunking strategy.

    Args:
        strategy: Chunking strategy
        db: Database session

    Returns:
        Default configuration for the strategy
    """
    # Return default configuration based on strategy
    if strategy == ChunkingStrategy.FIXED_TOKEN:
        return ChunkingConfig(
            strategy=strategy,
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=64,
            max_chunk_size=2048,
            preserve_whitespace=True,
            respect_sentence_boundaries=True,
        )
    if strategy == ChunkingStrategy.SLIDING_TOKEN:
        return ChunkingConfig(
            strategy=strategy,
            chunk_size=512,
            chunk_overlap=100,
            min_chunk_size=64,
            max_chunk_size=2048,
            preserve_whitespace=True,
            respect_sentence_boundaries=True,
        )
    if strategy == ChunkingStrategy.HEADING_AWARE:
        return ChunkingConfig(
            strategy=strategy,
            chunk_size=1024,
            chunk_overlap=50,
            min_chunk_size=128,
            max_chunk_size=4096,
            preserve_whitespace=True,
            respect_sentence_boundaries=False,  # Respect heading boundaries instead
        )
    # Default configuration for other strategies
    return ChunkingConfig(
        strategy=strategy,
        chunk_size=512,
        chunk_overlap=50,
        min_chunk_size=64,
        max_chunk_size=2048,
        preserve_whitespace=True,
        respect_sentence_boundaries=True,
    )
