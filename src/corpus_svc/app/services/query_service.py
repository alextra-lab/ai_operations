"""
Refactored query service for handling search operations.

This service implements the new design that tracks usage statistics
without storing chunk content in PostgreSQL. All chunk content is
retrieved from the vector database (Qdrant).
"""

import uuid
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ..clients.embedding_client import EmbeddingServiceClient, EmbeddingServiceError
from ..repositories.collection_repository import CollectionRepository
from ..repositories.document_repository import DocumentRepository
from ..repositories.usage_stats_repository import UsageStatsRepository
from ..repositories.vector_repository import QdrantRepository, QdrantSearchResult
from ..schemas.query import QueryResultItem, SearchFilter

logger = configure_logging(service_name="query_service")


class QueryService:
    """
    Refactored query service that uses centralized metadata and usage tracking.

    This service performs searches using the vector database for chunk content
    and the documents table for metadata, while tracking usage statistics.
    """

    def __init__(
        self,
        vector_repository: QdrantRepository,
        document_repository: DocumentRepository,
        usage_stats_repository: UsageStatsRepository,
        embedding_client: EmbeddingServiceClient,
        collection_repository: CollectionRepository,
    ):
        self.vector_repository = vector_repository
        self.document_repository = document_repository
        self.usage_stats_repository = usage_stats_repository
        self.embedding_client = embedding_client
        self.collection_repository = collection_repository

    async def _resolve_embedding_model_for_collections(
        self, collection_names: list[str]
    ) -> tuple[str, str]:
        """
        Resolve and validate embedding model and provider for the given collections.

        Ensures all specified collections exist, are active, and share the same
        embedding model and provider. Returns the shared embedding model and provider.

        Returns:
            Tuple of (embedding_model, embedding_provider)

        Raises:
            ValueError: If collections are missing, inactive, or use different
                embedding models or providers.
        """
        if not collection_names:
            raise ValueError("No collections specified")

        # Load collections by name
        collections = []
        for name in collection_names:
            coll = await self.collection_repository.get_by_name(name)
            if not coll:
                raise ValueError(f"Collection '{name}' not found")
            if not getattr(coll, "is_active", True):
                raise ValueError(f"Collection '{name}' is not active")
            collections.append(coll)

        # Validate same embedding model
        model_ids = set()
        provider_ids = set()
        for c in collections:
            model = getattr(c, "embedding_model", None)
            provider = getattr(c, "embedding_provider", None)
            if model is None or (isinstance(model, str) and not model.strip()):
                raise ValueError(
                    f"Collection '{getattr(c, 'name', 'unknown')}' has no embedding model"
                )
            if provider is None or (isinstance(provider, str) and not provider.strip()):
                raise ValueError(
                    f"Collection '{getattr(c, 'name', 'unknown')}' has no embedding provider"
                )
            model_ids.add(str(model))
            provider_ids.add(str(provider))

        if len(model_ids) != 1:
            details = ", ".join(
                f"{getattr(c, 'name', '')} ({getattr(c, 'embedding_model', '')})"
                for c in collections
            )
            raise ValueError(
                "Collections use different embedding models: "
                f"{details}. Select collections with the same embedding model."
            )

        if len(provider_ids) != 1:
            details = ", ".join(
                f"{getattr(c, 'name', '')} ({getattr(c, 'embedding_provider', '')})"
                for c in collections
            )
            raise ValueError(
                "Collections use different embedding providers: "
                f"{details}. Select collections with the same embedding provider."
            )

        return (str(next(iter(model_ids))), str(next(iter(provider_ids))))

    async def perform_semantic_search(
        self,
        query_text: str,
        top_k: int = 10,
        filters: list[SearchFilter] | None = None,
        user_id: str | None = None,
        min_relevancy_score: float = 0.0,
        auth_token: str | None = None,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        embedding_model: str | None = None,
        collection_names: list[str] | None = None,
    ) -> list[QueryResultItem]:
        """
        Perform semantic search using the refactored design.

        Args:
            query_text: The natural language query
            top_k: Number of results to return
            filters: Optional search filters
            user_id: Optional user ID for usage tracking
            min_relevancy_score: Minimum relevancy score threshold
            auth_token: Optional authentication token
            run_id: Optional run ID for usage tracking
            metadata: Optional metadata for usage tracking
            embedding_model: Optional embedding model to use (overrides default)

        Returns:
            List of search result items
        """
        if not self.embedding_client:
            logger.error("Embedding client is not available for query service")
            return []

        try:
            # Determine embedding model to use
            # ARCHITECTURE: Collections are authoritative for embedding model selection.
            # Use Cases do NOT dictate embedding models - they reference collections,
            # and collections define which embedding model to use (immutable after creation).
            # This ensures vector dimension consistency between stored documents and queries.
            provider_to_use = None
            if collection_names:
                # Collections are authoritative - use their embedding model and provider
                # This enforces ADR-021: Collection-Based Document Management
                model_to_use, provider_to_use = await self._resolve_embedding_model_for_collections(
                    collection_names
                )
                logger.info(
                    "Resolved from collections: model=%s, provider=%s (%s collection(s))",
                    model_to_use,
                    provider_to_use,
                    len(collection_names),
                )
            elif embedding_model:
                # Fall back to explicit parameter ONLY if no collections specified
                # This is a legacy path for backward compatibility
                model_to_use = embedding_model
                logger.info(f"Using explicit embedding model parameter: {model_to_use}")
            else:
                logger.error("No embedding model specified and no collections provided")
                return []

            logger.info(
                "Using embedding model: %s (provider: %s), query length=%s",
                model_to_use,
                provider_to_use or "auto-detect",
                len(query_text),
            )

            # Use provider-specific endpoint if provider is known, otherwise use OpenAI-compatible endpoint
            # When provider is explicitly resolved from collections, use it to avoid lookup overhead
            embedding_objects = await self.embedding_client.embed_texts(
                texts=[query_text],
                model=model_to_use,
                provider=provider_to_use,
                auth_token=auth_token,
            )
            if not embedding_objects or not embedding_objects[0].embedding:
                logger.error("Failed to get embedding for query (length=%s)", len(query_text))
                return []

            query_vector = embedding_objects[0].embedding

        except EmbeddingServiceError as e:
            logger.error(
                "Embedding service error for query (length=%s): %s",
                len(query_text),
                e,
                exc_info=True,
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error getting embedding for query (length=%s): %s",
                len(query_text),
                e,
                exc_info=True,
            )
            return []

        # 2. Convert SearchFilter list to Qdrant filter format
        qdrant_filters_payload: dict[str, Any] = {}
        if filters:
            for sf_item in filters:
                qdrant_filters_payload[sf_item.field] = sf_item.value

        # 3. Search Qdrant across one or more collections
        try:
            if collection_names and len(collection_names) > 0:
                logger.info(
                    "Searching %s collection(s)",
                    len(collection_names),
                )
                # Query each collection and merge results
                merged_results: list[QdrantSearchResult] = []
                for collection_name in collection_names:
                    try:
                        # Resolve database collection name to Qdrant collection name
                        collection = await self.collection_repository.get_by_name(collection_name)
                        if not collection:
                            logger.warning("Collection not found, skipping")
                            continue

                        qdrant_collection_name_raw = getattr(
                            collection, "qdrant_collection_name", None
                        )
                        if (
                            qdrant_collection_name_raw is None
                            or not isinstance(qdrant_collection_name_raw, str)
                            or not qdrant_collection_name_raw.strip()
                        ):
                            logger.warning("Collection has no valid Qdrant name, skipping")
                            continue

                        qdrant_collection_name = str(qdrant_collection_name_raw)

                        logger.info(
                            "Querying Qdrant collection (limit=%s)",
                            top_k * 2,
                        )

                        coll_results = await self.vector_repository.search_similar_in_collection(
                            collection_name=qdrant_collection_name,
                            query_vector=query_vector,
                            filter_params=qdrant_filters_payload,
                            limit=top_k * 2,
                        )

                        logger.info(
                            "Qdrant query returned %s results",
                            len(coll_results),
                        )

                        merged_results.extend(coll_results)
                    except Exception as e_coll:
                        logger.warning(
                            f"Collection search failed for '{collection_name}': {e_coll!s}"
                        )

                # Sort merged results by score and truncate to top_k
                merged_results.sort(key=lambda r: r.score, reverse=True)
                qdrant_results = merged_results[:top_k]

                if not qdrant_results:
                    logger.warning(
                        f"No results found from Qdrant after querying {len(collection_names)} collection(s): {collection_names}"
                    )
            else:
                # Default: search in configured repository collection
                logger.info("No collection names specified, using default repository collection")
                qdrant_results = await self.vector_repository.search_similar(
                    query_vector=query_vector,
                    filter_params=qdrant_filters_payload,
                    limit=top_k,
                )
                logger.info(f"Default collection search returned {len(qdrant_results)} results")
        except Exception as e:
            logger.error(
                "Error searching Qdrant: %s",
                e,
                exc_info=True,
            )
            return []

        # 4. Filter by minimum relevancy score
        if not qdrant_results:
            return []

        filtered_results = [hit for hit in qdrant_results if hit.score >= min_relevancy_score]

        # 5. Hydrate results with document metadata
        hydrated_results: list[QueryResultItem] = []
        document_access_tracking: dict[str, list[uuid.UUID]] = {}  # doc_id -> chunk_ids
        relevancy_scores: dict[str, list[float]] = {}  # doc_id -> scores

        for hit in filtered_results:
            try:
                chunk_id_str = hit.payload.get("chunk_id")
                doc_id_str = hit.payload.get("document_id")

                if not chunk_id_str or not doc_id_str:
                    logger.warning(f"Qdrant hit missing chunk_id or document_id: {hit.id}")
                    continue

                chunk_id = uuid.UUID(chunk_id_str)
                doc_id = uuid.UUID(doc_id_str)

                # Get document metadata from documents table
                document = await self.document_repository.get_document_by_id(doc_id)
                if not document:
                    logger.warning(f"Could not find document {doc_id} for Qdrant hit {hit.id}")
                    continue

                # Extract chunk content from vector DB payload
                text_content = hit.payload.get("text", "")
                chunk_metadata = hit.payload.get("metadata", {})

                # Create result item - ensure metadata is a dict[str, Any]
                doc_metadata: dict[str, Any] = {}
                if getattr(document, "metadata_", None) is not None and isinstance(
                    document.metadata_, dict
                ):
                    doc_metadata = document.metadata_  # type: ignore[assignment]

                # Enrich metadata with document fields needed by response formatter
                file_type_val = getattr(document, "file_type", None) or "text"
                created_at_val = getattr(document, "created_at", None)
                enriched_metadata = {
                    **doc_metadata,
                    "document_type": file_type_val,
                    "file_type": file_type_val,
                    "document_classification": getattr(document, "classification", None),
                    "classification": getattr(document, "classification", None),
                    "document_author": getattr(document, "author", None),
                    "author": getattr(document, "author", None),
                    "created_at": created_at_val.isoformat() if created_at_val else None,
                    "created_date": created_at_val.isoformat() if created_at_val else None,
                    "source": getattr(document, "source", None),
                    "chunk_index": chunk_metadata.get("chunk_index", 0),
                    "content": text_content,
                }

                item = QueryResultItem(
                    document_id=str(doc_id),
                    chunk_id=str(chunk_id),
                    score=hit.score,
                    text_snippet=(
                        text_content[:200] + "..." if len(text_content) > 200 else text_content
                    ),
                    full_text=text_content,
                    document_title=document.title,  # type: ignore
                    document_source=document.source,  # type: ignore
                    document_author=document.author,  # type: ignore
                    document_metadata=enriched_metadata,
                    chunk_metadata=chunk_metadata,
                )
                hydrated_results.append(item)

                # Track for usage statistics
                doc_id_str = str(doc_id)
                if doc_id_str not in document_access_tracking:
                    document_access_tracking[doc_id_str] = []
                    relevancy_scores[doc_id_str] = []

                document_access_tracking[doc_id_str].append(chunk_id)
                relevancy_scores[doc_id_str].append(hit.score)

            except Exception as e:
                logger.error(
                    f"Error hydrating search result for Qdrant hit {hit.id}: {e}",
                    exc_info=True,
                )
                continue

        logger.info(
            "Semantic search completed: results=%s",
            len(hydrated_results),
            extra={"user_id": user_id},
        )

        # Record usage statistics for semantic search
        for doc_id_str, chunk_id_list in document_access_tracking.items():
            logger.debug(
                "Usage stats: doc_id=%s, chunk_count=%s",
                doc_id_str,
                len(chunk_id_list),
            )
            try:
                # Ensure run_id is a UUID or None
                run_id_uuid = (
                    uuid.UUID(run_id) if run_id is not None and isinstance(run_id, str) else run_id
                )
                await self.usage_stats_repository.record_retrieval(
                    document_id=uuid.UUID(doc_id_str),
                    chunk_ids=chunk_id_list,
                    user_id=user_id,
                    query_text=query_text,
                    relevancy_scores=relevancy_scores.get(doc_id_str, []),
                    metadata=metadata,
                    run_id=run_id_uuid,
                )
            except Exception as e:
                logger.error(f"Failed to record usage stats for doc {doc_id_str}: {e}")

        return hydrated_results

    async def perform_hybrid_search(
        self,
        query_text: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: list[SearchFilter] | None = None,
        user_id: str | None = None,
        min_relevancy_score: float = 0.0,
        auth_token: str | None = None,
    ) -> list[QueryResultItem]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query_text: The natural language query
            top_k: Number of results to return
            semantic_weight: Weight for semantic search results
            keyword_weight: Weight for keyword search results
            filters: Optional search filters
            user_id: Optional user ID for usage tracking
            min_relevancy_score: Minimum relevancy score threshold

        Returns:
            List of search result items
        """
        # For now, implement as semantic search with keyword filtering
        # A full hybrid implementation would require keyword search capabilities
        # in the vector database or a separate text search index

        # Add keyword filtering to the existing filters
        if filters is None:
            filters = []

        # Simple keyword filtering by adding text content filter
        # This is a simplified implementation - a full hybrid search would
        # require more sophisticated ranking combination

        results = await self.perform_semantic_search(
            query_text=query_text,
            top_k=top_k,
            filters=filters,
            user_id=user_id,
            min_relevancy_score=min_relevancy_score,
            auth_token=auth_token,
        )

        # Apply keyword scoring adjustment
        for result in results:
            # Simple keyword matching boost
            keyword_matches = sum(
                1
                for word in query_text.lower().split()
                if result.full_text and word in result.full_text.lower()
            )
            keyword_score = keyword_matches / len(query_text.split()) if query_text.split() else 0

            # Combine scores
            result.score = (semantic_weight * result.score) + (keyword_weight * keyword_score)

        # Re-sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)

        # Update usage tracking metadata to indicate hybrid search
        # Note: This is a simplified approach - in a full implementation,
        # you'd want to track the hybrid search as a separate event

        return results[:top_k]

    async def get_document_chunks(
        self,
        document_id: str,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[QueryResultItem]:
        """
        Get all chunks for a specific document.

        Args:
            document_id: Document ID
            user_id: Optional user ID for usage tracking
            limit: Maximum number of chunks to return

        Returns:
            List of document chunks
        """
        try:
            doc_uuid = uuid.UUID(document_id)

            # Get document metadata
            document = await self.document_repository.get_document_by_id(doc_uuid)
            if not document:
                logger.warning(f"Document {document_id} not found")
                return []

            # Search for all chunks of this document in vector DB
            qdrant_results = await self.vector_repository.search_similar(
                query_vector=[],  # No vector search, just filter
                filter_params={"document_id": document_id},
                limit=limit,
            )

            # Convert to result items
            results = []
            chunk_ids = []

            for hit in qdrant_results:
                chunk_id_str = hit.payload.get("chunk_id")
                if not chunk_id_str:
                    continue

                chunk_id = uuid.UUID(chunk_id_str)
                chunk_ids.append(chunk_id)

                text_content = hit.payload.get("text", "")
                chunk_metadata = hit.payload.get("metadata", {})

                # Create result item - ensure metadata is a dict
                doc_metadata: dict[str, Any] = {}
                if getattr(document, "metadata_", None) is not None and isinstance(
                    document.metadata_, dict
                ):
                    doc_metadata = document.metadata_  # type: ignore[assignment]

                item = QueryResultItem(
                    document_id=document_id,
                    chunk_id=str(chunk_id),
                    score=1.0,  # No relevancy scoring for document browsing
                    text_snippet=(
                        text_content[:200] + "..." if len(text_content) > 200 else text_content
                    ),
                    full_text=text_content,
                    document_title=document.title,  # type: ignore
                    document_source=document.source,  # type: ignore
                    document_metadata=doc_metadata,
                    chunk_metadata=chunk_metadata,
                )
                results.append(item)

            # Record usage statistics for document browsing
            if chunk_ids and user_id:
                logger.debug(
                    f"[DEBUG] Usage stats (doc browse): doc_id={doc_uuid}, chunk_ids={chunk_ids}"
                )
                try:
                    await self.usage_stats_repository.record_retrieval(
                        document_id=doc_uuid,
                        chunk_ids=chunk_ids,
                        user_id=user_id,
                        query_text=None,  # No query for document browsing
                        relevancy_scores=None,
                        metadata={
                            "access_type": "document_browse",
                            "chunks_retrieved": len(chunk_ids),
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to record usage stats for document browsing {document_id}: {e}"
                    )

            logger.info(f"Retrieved {len(results)} chunks for document {document_id}")
            return results

        except Exception as e:
            logger.error(
                f"Error retrieving chunks for document {document_id}: {e}",
                exc_info=True,
            )
            return []

    async def get_similar_documents(
        self,
        document_id: str,
        top_k: int = 5,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find documents similar to the given document.

        Args:
            document_id: Reference document ID
            top_k: Number of similar documents to return
            user_id: Optional user ID for usage tracking

        Returns:
            List of similar documents with metadata
        """
        try:
            doc_uuid = uuid.UUID(document_id)

            # Get the reference document
            document = await self.document_repository.get_document_by_id(doc_uuid)
            if not document:
                logger.warning(f"Reference document {document_id} not found")
                return []

            # Get a representative chunk from the document to use as query
            doc_chunks = await self.vector_repository.search_similar(
                query_vector=[],
                filter_params={"document_id": document_id},
                limit=1,
            )

            if not doc_chunks:
                logger.warning(f"No chunks found for reference document {document_id}")
                return []

            # Use the first chunk's embedding to find similar content
            # This is a simplified approach - a better implementation might
            # use document-level embeddings or aggregate chunk embeddings

            # For now, return empty list as this requires more complex vector operations
            # that would need to be implemented in the vector repository
            logger.info(
                "Similar documents search not fully implemented for document %s (top_k=%s, user_id=%s)",
                document_id,
                top_k,
                user_id,
            )
            return []

        except Exception as e:
            logger.error(f"Error finding similar documents for {document_id}: {e}", exc_info=True)
            return []

    async def get_query_suggestions(
        self,
        partial_query: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get query suggestions based on partial input.

        Args:
            partial_query: Partial query text
            limit: Maximum number of suggestions

        Returns:
            List of suggested queries
        """
        try:
            # Get popular queries that start with the partial query
            # This uses the usage statistics to find common query patterns
            suggestions = await self.usage_stats_repository.get_query_patterns(
                limit=limit * 2  # Get more to filter
            )

            # Filter suggestions that match the partial query
            filtered_suggestions = [
                pattern["query_text"]
                for pattern in suggestions
                if pattern["query_text"]
                and pattern["query_text"].lower().startswith(partial_query.lower())
            ]

            return filtered_suggestions[:limit]

        except Exception as e:
            logger.error(
                f"Error getting query suggestions for '{partial_query}': {e}",
                exc_info=True,
            )
            return []
