"""
Refactored API router for search and retrieval operations.

This router implements the new design that uses centralized metadata
and tracks usage statistics without storing chunk content in PostgreSQL.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..clients.embedding_client import EmbeddingServiceClient
from ..db.connection import get_db_session
from ..repositories.collection_repository import CollectionRepository
from ..repositories.document_repository import DocumentRepository
from ..repositories.usage_stats_repository import UsageStatsRepository
from ..repositories.vector_repository import QdrantRepository, get_vector_repository
from ..schemas.query import (
    HybridSearchRequest,
    QueryRequest,
    QueryResponse,
    QuerySuggestionsResponse,
)
from ..services.query_service import QueryService
from ..utils.auth import extract_jwt_token, extract_user_id_from_token, get_current_user
from ..utils.embeddings import get_embedding_client

logger = configure_logging(service_name="query_router")

router = APIRouter()


def get_forward_headers(request: Request) -> dict[str, str]:
    """Extract JWT token from Authorization header for forwarding."""
    headers = {}
    if "authorization" in request.headers:
        headers["authorization"] = request.headers["authorization"]
    return headers


async def get_query_service_refactored(
    session: AsyncSession = Depends(get_db_session),
    vector_repo: QdrantRepository = Depends(get_vector_repository),
    embedding_client: EmbeddingServiceClient | None = Depends(get_embedding_client),
) -> QueryService:
    """Get refactored query service with dependencies."""
    if not embedding_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service is not available or not configured.",
        )

    # Initialize repositories with the session
    document_repo = DocumentRepository(session)
    usage_stats_repo = UsageStatsRepository(session)
    collection_repo = CollectionRepository(session)

    return QueryService(
        vector_repository=vector_repo,
        document_repository=document_repo,
        usage_stats_repository=usage_stats_repo,
        embedding_client=embedding_client,
        collection_repository=collection_repo,
    )


@router.post(
    "/semantic-search",
    response_model=QueryResponse,
    summary="Perform semantic search using refactored design",
    status_code=status.HTTP_200_OK,
)
async def semantic_search(
    query_request: QueryRequest,
    request: Request,
    query_service: QueryService = Depends(get_query_service_refactored),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> QueryResponse:
    """
    Perform semantic search using the refactored design.

    This endpoint uses the vector database for chunk content and the documents
    table for metadata, while tracking usage statistics.
    """
    try:
        # Extract user ID for usage tracking
        user_uuid = extract_user_id_from_token(current_user)
        user_id_str = str(user_uuid)

        # Extract JWT token for forwarding to embedding service
        jwt_token = extract_jwt_token(request)

        logger.info(
            f"Semantic search query: {query_request.query_text}, top_k: {query_request.top_k}, user: {user_id_str}, run_id: {query_request.run_id}"
        )

        # Perform semantic search
        results = await query_service.perform_semantic_search(
            query_text=query_request.query_text,
            top_k=query_request.top_k,
            filters=query_request.filters,
            user_id=user_id_str,
            min_relevancy_score=getattr(query_request, "min_relevancy_score", 0.0),
            auth_token=jwt_token,
            run_id=query_request.run_id,  # Use run_id from request body
            metadata=getattr(query_request, "metadata", None),
            embedding_model=getattr(query_request, "embedding_model", None),
            collection_names=query_request.collection_names,
        )

        return QueryResponse(
            query_id=str(uuid.uuid4()),
            query_text=query_request.query_text,
            search_type="semantic",
            results=results,
            total_results=len(results),
            processing_time_ms=0,  # Could be tracked if needed
        )

    except Exception as e:
        logger.error(f"Error during semantic search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during semantic search: {e!s}",
        )


@router.post(
    "/hybrid-search",
    response_model=QueryResponse,
    summary="Perform hybrid search combining semantic and keyword search",
    status_code=status.HTTP_200_OK,
)
async def hybrid_search(
    search_request: HybridSearchRequest,
    request: Request,
    query_service: QueryService = Depends(get_query_service_refactored),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> QueryResponse:
    """
    Perform hybrid search combining semantic and keyword search.

    This endpoint combines semantic similarity with keyword matching
    for more comprehensive search results.
    """
    try:
        # Extract user ID for usage tracking
        user_uuid = extract_user_id_from_token(current_user)
        user_id_str = str(user_uuid)

        # Extract JWT token for forwarding to embedding service
        jwt_token = extract_jwt_token(request)

        logger.info(
            f"Hybrid search query: {search_request.query_text}, semantic_weight: {search_request.semantic_weight}, "
            f"keyword_weight: {search_request.keyword_weight}, user: {user_id_str}"
        )

        # Perform hybrid search
        results = await query_service.perform_hybrid_search(
            query_text=search_request.query_text,
            top_k=search_request.top_k,
            semantic_weight=search_request.semantic_weight,
            keyword_weight=search_request.keyword_weight,
            filters=search_request.filters,
            user_id=user_id_str,
            min_relevancy_score=getattr(search_request, "min_relevancy_score", 0.0),
            auth_token=jwt_token,
        )

        return QueryResponse(
            query_id=str(uuid.uuid4()),
            query_text=search_request.query_text,
            search_type="hybrid",
            results=results,
            total_results=len(results),
            processing_time_ms=0,
        )

    except Exception as e:
        logger.error(f"Error during hybrid search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during hybrid search: {e!s}",
        )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=QueryResponse,
    summary="Get all chunks for a specific document",
    status_code=status.HTTP_200_OK,
)
async def get_document_chunks(
    document_id: str,
    limit: int = Query(100, description="Maximum number of chunks to return"),
    query_service: QueryService = Depends(get_query_service_refactored),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> QueryResponse:
    """
    Get all chunks for a specific document.

    This endpoint retrieves all chunks for a document from the vector database
    and tracks the access for analytics.
    """
    try:
        # Extract user ID for usage tracking
        user_uuid = extract_user_id_from_token(current_user)
        user_id_str = str(user_uuid)

        logger.info(f"Getting chunks for document {document_id}, user: {user_id_str}")

        # Get document chunks
        results = await query_service.get_document_chunks(
            document_id=document_id,
            user_id=user_id_str,
            limit=limit,
        )

        return QueryResponse(
            query_id=str(uuid.uuid4()),
            query_text=None,
            search_type="document_browse",
            results=results,
            total_results=len(results),
            processing_time_ms=0,
        )

    except Exception as e:
        logger.error(f"Error getting document chunks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred getting document chunks: {e!s}",
        )


@router.get(
    "/suggestions",
    response_model=QuerySuggestionsResponse,
    summary="Get query suggestions based on partial input",
    status_code=status.HTTP_200_OK,
)
async def get_query_suggestions(
    partial_query: str = Query(..., description="Partial query text"),
    limit: int = Query(5, description="Maximum number of suggestions"),
    query_service: QueryService = Depends(get_query_service_refactored),
) -> QuerySuggestionsResponse:
    """
    Get query suggestions based on partial input.

    This endpoint uses usage statistics to suggest popular queries
    that match the partial input.
    """
    try:
        logger.info(f"Getting query suggestions for: {partial_query}")

        suggestions = await query_service.get_query_suggestions(
            partial_query=partial_query,
            limit=limit,
        )

        return QuerySuggestionsResponse(
            partial_query=partial_query,
            suggestions=suggestions,
        )

    except Exception as e:
        logger.error(f"Error getting query suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred getting query suggestions: {e!s}",
        )


@router.get(
    "/documents/{document_id}/similar",
    response_model=list[dict[str, Any]],
    summary="Find documents similar to the given document",
    status_code=status.HTTP_200_OK,
)
async def get_similar_documents(
    document_id: str,
    top_k: int = Query(5, description="Number of similar documents to return"),
    query_service: QueryService = Depends(get_query_service_refactored),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Find documents similar to the given document.

    This endpoint finds documents with similar content based on
    vector similarity in the embedding space.
    """
    try:
        # Extract user ID for usage tracking
        user_uuid = extract_user_id_from_token(current_user)
        user_id_str = str(user_uuid)

        logger.info(f"Finding similar documents for {document_id}, user: {user_id_str}")

        return await query_service.get_similar_documents(
            document_id=document_id,
            top_k=top_k,
            user_id=user_id_str,
        )

    except Exception as e:
        logger.error(f"Error finding similar documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred finding similar documents: {e!s}",
        )


# Legacy endpoint for backward compatibility
@router.post(
    "/",
    response_model=QueryResponse,
    summary="Legacy search endpoint (redirects to semantic search)",
    status_code=status.HTTP_200_OK,
)
async def legacy_search(
    request: Request,
    query_text: str = Query(..., description="Search query text"),
    top_k: int = Query(10, description="Number of results to return"),
    query_service: QueryService = Depends(get_query_service_refactored),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> QueryResponse:
    """
    Legacy search endpoint for backward compatibility.

    This endpoint maintains compatibility with the old API while
    using the new refactored design internally.
    """
    try:
        # Extract user ID for usage tracking
        user_uuid = extract_user_id_from_token(current_user)
        user_id_str = str(user_uuid)

        # Extract JWT token for forwarding to embedding service
        jwt_token = extract_jwt_token(request)

        logger.info(f"Legacy search query: {query_text}, top_k: {top_k}, user: {user_id_str}")

        # Perform semantic search (default behavior)
        results = await query_service.perform_semantic_search(
            query_text=query_text,
            top_k=top_k,
            filters=None,
            user_id=user_id_str,
            min_relevancy_score=0.0,
            auth_token=jwt_token,
        )

        return QueryResponse(
            query_id=str(uuid.uuid4()),
            query_text=query_text,
            search_type="semantic",
            results=results,
            total_results=len(results),
            processing_time_ms=0,
        )

    except Exception as e:
        logger.error(f"Error during legacy search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search: {e!s}",
        )
