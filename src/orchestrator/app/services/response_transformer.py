"""
Response Transformer Service for AI Operations Platform.

This service transforms internal service responses into frontend-compatible
schemas, ensuring consistent API contracts and proper field mapping.

The backend is the golden source of truth. This service adapts backend
responses to match documented frontend interfaces without changing core
business logic.
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="response_transformer")


class ResponseTransformer:
    """
    Transforms internal service responses into frontend-compatible schemas.

    This service acts as an adapter layer between backend services and the UI,
    ensuring consistent API contracts while preserving backend data integrity.

    Design Principles:
    - Backend schemas are the golden source
    - Transformations are stateless and pure
    - No data loss during transformation
    - Comprehensive logging for debugging
    """

    @staticmethod
    def transform_retrieval_result(backend_result: dict[str, Any]) -> dict[str, Any]:
        """
        Transform QueryResultItem from retrieval service into frontend
        SearchResult.

        Backend Schema (QueryResultItem from retrieval service):
            document_id: str - UUID of source document
            chunk_id: str - UUID of chunk
            score: float - Cosine similarity (0.0-1.0)
            text_snippet: str | None - Short excerpt
            full_text: str | None - Complete chunk text
            document_title: str | None - Document title
            document_source: str | None - Source file/URL
            document_author: str | None - Document author
            document_metadata: dict | None - Document metadata
            chunk_metadata: dict | None - Chunk-specific metadata

        Frontend Schema (SearchResult):
            id: str - Unique identifier
            title: str - Display title
            content: str - Full content
            snippet: str - Text excerpt
            relevance_score: float - Relevance (0.0-1.0)
            confidence: float - Confidence (0.0-1.0)
            metadata: dict - Flattened metadata

        Args:
            backend_result: QueryResultItem from retrieval service

        Returns:
            Transformed result matching frontend SearchResult interface
        """
        # Extract and flatten document metadata
        doc_metadata = backend_result.get("document_metadata") or {}
        chunk_metadata = backend_result.get("chunk_metadata") or {}

        # Use score for both relevance and confidence
        # Note: Retrieval service provides vector similarity, not semantic
        # confidence
        score = backend_result.get("score", 0.0)

        # Build flattened metadata structure
        metadata = {
            # Core document metadata
            "author": backend_result.get("document_author")
            or doc_metadata.get("author", "Unknown"),
            "source": backend_result.get("document_source", ""),
            "classification": doc_metadata.get("classification", ""),
            "tags": doc_metadata.get("tags", []),
            # Temporal metadata
            "created_date": doc_metadata.get("created_at"),
            "modified_date": doc_metadata.get("updated_at"),
            # File metadata
            "file_type": doc_metadata.get("file_type"),
            "file_size": doc_metadata.get("file_size"),
            # Chunk metadata
            "chunk_index": chunk_metadata.get("chunk_index"),
        }

        # Add any additional metadata fields not explicitly mapped
        for key, value in doc_metadata.items():
            if key not in metadata and value is not None:
                metadata[key] = value

        # Build transformed result
        return {
            "id": backend_result.get("chunk_id", backend_result.get("document_id", "")),
            "title": backend_result.get("document_title") or "Untitled Document",
            "content": (backend_result.get("full_text") or backend_result.get("text_snippet", "")),
            "snippet": backend_result.get("text_snippet", ""),
            "source_type": "CHUNK",
            "document_id": backend_result.get("document_id"),
            "chunk_index": chunk_metadata.get("chunk_index"),
            "relevance_score": score,
            "confidence": score,  # Use score as confidence proxy
            "metadata": metadata,
            "highlighted_content": None,  # Future enhancement
        }

    @staticmethod
    def transform_retrieval_response(
        backend_response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Transform QueryResponse from retrieval service into
        SemanticSearchResponse.

        Backend Schema (QueryResponse):
            query_id: str
            query_text: str | None
            search_type: str
            results: QueryResultItem[]
            total_results: int
            processing_time_ms: float

        Frontend Schema (SemanticSearchResponse):
            results: SearchResult[]
            total_count: int
            query_id: str
            processing_time_ms: number
            search_metadata: dict
            pagination: dict

        Args:
            backend_response: QueryResponse from retrieval service

        Returns:
            Transformed response matching frontend SemanticSearchResponse
            interface
        """
        # Transform each result item
        results = backend_response.get("results", [])
        transformed_results = [
            ResponseTransformer.transform_retrieval_result(result) for result in results
        ]

        # Calculate pagination (basic for now)
        total_results = backend_response.get("total_results", len(transformed_results))
        page_size = len(transformed_results)

        # Build complete response
        response = {
            "results": transformed_results,
            "total_count": total_results,
            "query_id": backend_response.get("query_id", ""),
            "processing_time_ms": backend_response.get("processing_time_ms", 0.0),
            "search_metadata": {
                "search_type": backend_response.get("search_type", "semantic"),
                "filters_applied": {},  # Future: extract from request
                "sort_applied": {},  # Future: extract from request
                "suggestions": [],  # Future: implement suggestions
                "related_queries": [],  # Future: implement related queries
            },
            "pagination": {
                "current_page": 1,
                "total_pages": 1,
                "page_size": page_size,
                "has_next": False,
                "has_previous": False,
            },
        }

        logger.debug(
            "Transformed retrieval response",
            extra={
                "original_results": len(results),
                "transformed_results": len(transformed_results),
                "query_id": response["query_id"],
            },
        )

        return response
