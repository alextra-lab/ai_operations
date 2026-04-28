"""
Qdrant vector store repository.

This module provides a repository for interacting with Qdrant vector database,
handling vector storage, retrieval, and collection management.
"""

import asyncio  # Added for potential sleep/retry logic if needed elsewhere
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient  # Explicitly import AsyncQdrantClient
from qdrant_client import models as qdrant_models

from shared.config.loader import is_testing_environment, load_qdrant_config
from shared.logging_utils.fastapi import configure_logging

# Configure logger using shared logging utilities
logger = configure_logging(service_name="vector_repository")


class VectorRepositoryConfig(BaseModel):
    """Configuration for Qdrant vector repository."""

    # Qdrant connection settings
    url: str = Field(..., description="URL of the Qdrant server")
    port: int | None = Field(None, description="Port of the Qdrant server")
    api_key: str | None = Field(None, description="API key for Qdrant authentication")
    prefer_grpc: bool = Field(False, description="Whether to prefer gRPC over HTTP")
    timeout: float | None = Field(
        10.0, description="Timeout for Qdrant operations in seconds"
    )  # Changed to Optional[float]

    # Collection settings
    collection_name: str = Field("documents", description="Name of the main collection")
    vector_size: int = Field(384, description="Size of embedding vectors")
    distance: str = Field(
        "COSINE",
        description="Distance function for similarity search",
    )

    # Index settings
    m: int = Field(16, description="Number of bi-directional links in HNSW graph")
    ef_construct: int = Field(100, description="Size of the dynamic list for ef_construct")
    ef_search: int = Field(128, description="Size of the dynamic list for ef_search")

    # Search settings
    default_limit: int = Field(10, description="Default number of results to return")
    default_offset: int = Field(0, description="Default offset for pagination")
    indexing_threshold: int = Field(
        20000, description="Number of vectors before enabling HNSW indexing"
    )

    # Pydantic config to handle API schema changes between Qdrant client and server versions
    model_config = {"extra": "allow"}


class QdrantSearchResult(BaseModel):
    """Result from Qdrant search operation."""

    id: str = Field(..., description="ID of the vector")
    score: float = Field(..., description="Similarity score")
    payload: dict[str, Any] = Field(default_factory=dict, description="Associated payload")
    document_id: str | None = Field(None, description="ID of the parent document")
    chunk_id: str | None = Field(None, description="ID of the associated chunk")


class VectorSearchParams(BaseModel):
    """Parameters for vector search operations."""

    query_vector: list[float] = Field(..., description="Query vector for similarity search")
    filter: dict[str, Any] | None = Field(None, description="Filter for search results")
    limit: int = Field(10, description="Maximum number of results to return")
    offset: int = Field(0, description="Offset for pagination")
    with_payload: bool = Field(True, description="Whether to include payload in results")
    score_threshold: float | None = Field(None, description="Minimum similarity score threshold")


class QdrantRepository:
    """
    Repository for vector storage and retrieval using Qdrant.

    This class provides methods for:
    - Initializing and managing Qdrant collections
    - Storing vectors with associated metadata
    - Searching for similar vectors with filtering
    - Managing vector indexes for efficient retrieval
    """

    _client: AsyncQdrantClient | None = None  # Changed to AsyncQdrantClient

    def __init__(self, config: VectorRepositoryConfig):
        """
        Initialize the Qdrant repository.

        Args:
            config: Configuration for the repository
        """
        self.config = config
        # Client will be initialized lazily in _get_client
        logger.info(
            f"QdrantRepository configured with: {config.url}, collection: {config.collection_name}"
        )

    async def _get_client(self) -> AsyncQdrantClient:
        """Initializes and returns the AsyncQdrantClient session."""
        if self._client is None:
            logger.info(
                f"Initializing AsyncQdrantClient: url={self.config.url}, port={self.config.port}, prefer_grpc={self.config.prefer_grpc}"
            )
            timeout_val: int | None = None
            if self.config.timeout is not None:
                timeout_val = int(self.config.timeout)

            self._client = AsyncQdrantClient(
                url=self.config.url,
                port=self.config.port,
                api_key=self.config.api_key,
                prefer_grpc=self.config.prefer_grpc,
                timeout=timeout_val,  # Use casted value
            )
            try:
                # A simple operation to check connectivity
                # Add retries specifically for testing environment if initial connection fails
                if is_testing_environment():
                    max_retries = 5
                    retry_delay = 2  # seconds
                    for attempt in range(max_retries):
                        try:
                            await self._client.get_collections()
                            logger.info(
                                f"AsyncQdrantClient connected successfully on attempt {attempt + 1}."
                            )
                            break
                        except Exception as e_retry:
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Qdrant connection attempt {attempt + 1} failed: {e_retry}. Retrying in {retry_delay}s..."
                                )
                                await asyncio.sleep(retry_delay)
                            else:
                                logger.error(
                                    f"All {max_retries} Qdrant connection attempts failed. Last error: {e_retry}",
                                    exc_info=True,
                                )
                                raise  # Re-raise the last exception if all retries fail
                else:
                    await self._client.get_collections()
                    logger.info("AsyncQdrantClient connected successfully.")
            except Exception as e:
                logger.error(
                    f"Failed to connect to Qdrant during client initialization: {e}",
                    exc_info=True,
                )
                # Allow operations to fail if connection isn't established, or raise here if not testing
                if not is_testing_environment():  # Only raise if not in testing
                    raise
        return self._client

    async def initialize_collection(self, force_recreate: bool = False) -> bool:
        """
        Initialize the Qdrant collection.

        This method creates the collection if it doesn't exist, or validates
        the existing collection against the configuration.

        Args:
            force_recreate: Whether to force recreation of the collection if it exists

        Returns:
            True if the collection was created or already exists with correct configuration
        """
        client = await self._get_client()
        try:
            # Check if collection exists
            collections_response = await client.get_collections()
            collection_names = [c.name for c in collections_response.collections]

            # If collection exists and we're not forcing recreation, validate it
            if self.config.collection_name in collection_names and not force_recreate:
                logger.info(
                    f"Collection {self.config.collection_name} already exists, validating..."
                )

                try:
                    # Get collection info - handle potential validation errors
                    collection_info = await client.get_collection(self.config.collection_name)

                    # Extract vector size safely
                    vector_size = 0
                    if (
                        collection_info.config
                        and collection_info.config.params
                        and hasattr(collection_info.config.params, "vectors")
                    ):
                        vectors_config = collection_info.config.params.vectors
                        if isinstance(vectors_config, qdrant_models.VectorParams):
                            vector_size = int(vectors_config.size)  # type: ignore[arg-type]
                        elif (
                            isinstance(vectors_config, dict) and "size" in vectors_config
                        ):  # For older client versions or different structures
                            vector_size = int(vectors_config["size"])  # type: ignore[arg-type,call-overload]
                        elif hasattr(vectors_config, "size"):  # General attribute check
                            _raw = getattr(vectors_config, "size", 0)  # type: ignore[assignment]
                            # Client may type .size as VectorParams; always coerce to int
                            if isinstance(_raw, int):
                                vector_size = _raw
                            else:
                                _nested = getattr(_raw, "size", 0)
                                vector_size = int(_nested) if isinstance(_nested, int) else 0

                    if not vector_size:  # Fallback if not found in common new path
                        try:
                            if hasattr(collection_info.config.params, "vector_size"):  # type: ignore[attr-defined]
                                raw = collection_info.config.params.vector_size  # type: ignore[attr-defined]
                                vector_size = (
                                    int(raw)
                                    if isinstance(raw, int)
                                    else int(getattr(raw, "size", 0))
                                )
                            elif hasattr(collection_info.config, "vector_size"):  # type: ignore[attr-defined]
                                raw = collection_info.config.vector_size  # type: ignore[attr-defined]
                                vector_size = (
                                    int(raw)
                                    if isinstance(raw, int)
                                    else int(getattr(raw, "size", 0))
                                )
                        except Exception as e_fallback:
                            logger.warning(
                                f"Could not extract vector size using fallback paths: {e_fallback!s}"
                            )

                    if not vector_size:
                        logger.warning(
                            f"Vector size could not be determined from collection_info: {collection_info}"
                        )

                    # Validate vector size if we could extract it
                    if vector_size and vector_size != self.config.vector_size:
                        logger.warning(
                            f"Existing collection has vector size {vector_size}, "
                            f"but configuration specifies {self.config.vector_size}"
                        )
                        if force_recreate:
                            logger.warning(f"Recreating collection {self.config.collection_name}")
                            await client.delete_collection(self.config.collection_name)
                        else:
                            # We'll work with the existing collection but log a warning
                            logger.warning("Using existing collection with different vector size")

                    logger.info(f"Collection {self.config.collection_name} validated")
                    return True

                except Exception as e:
                    logger.warning(f"Collection validation failed: {e!s}")
                    if force_recreate:
                        logger.warning("Recreating collection due to validation failure")
                        try:
                            await client.delete_collection(self.config.collection_name)
                        except Exception as del_e:
                            logger.error(f"Failed to delete collection: {del_e!s}")
                            return False
                    else:
                        # Continue with existing collection despite validation failure
                        logger.info("Using existing collection despite validation failure")
                        return True

            # If collection exists and we're forcing recreation, delete it
            if self.config.collection_name in collection_names and force_recreate:
                logger.info(f"Deleting existing collection {self.config.collection_name}")
                await client.delete_collection(self.config.collection_name)

            # Create the collection
            logger.info(f"Creating collection {self.config.collection_name}")

            # Define vector configuration
            vectors_config = qdrant_models.VectorParams(
                size=self.config.vector_size,
                distance=qdrant_models.Distance[
                    self.config.distance.upper()
                ],  # Use .upper() for robustness
            )

            # Define index configuration (HNSW parameters)
            hnsw_config = qdrant_models.HnswConfigDiff(
                m=self.config.m,
                ef_construct=self.config.ef_construct,
            )

            # Define optimizers configuration - default to auto indexing
            # Use 0 for test environments to index immediately, 20000 for production
            indexing_threshold = self.config.indexing_threshold
            optimizers_config = qdrant_models.OptimizersConfigDiff(
                indexing_threshold=indexing_threshold
            )

            # Create the collection with error handling for version compatibility
            try:
                await client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=vectors_config,
                    hnsw_config=hnsw_config,
                    optimizers_config=optimizers_config,
                )
            except TypeError as te:
                # Handle potential argument compatibility issues
                logger.warning(f"Failed with TypeError, trying alternative signature: {te!s}")
                # Try without optimizers_config which might be causing issues
                await client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=vectors_config,
                    hnsw_config=hnsw_config,
                )

            # Add payload indexes for efficient filtering
            try:
                await self._create_payload_indexes(client)  # Pass client
            except Exception as idx_e:
                logger.warning(f"Failed to create payload indexes: {idx_e!s}")
                # Continue without indexes - they're not critical

            logger.info(f"Collection {self.config.collection_name} created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize collection: {e!s}", exc_info=True)
            # Don't re-raise, return False to indicate failure but allow service to start
            return False

    async def _create_payload_indexes(
        self, client: AsyncQdrantClient
    ) -> None:  # Added client parameter
        """
        Create payload indexes for efficient filtering.

        This method creates indexes on commonly used filter fields.
        """
        try:
            # Index for document_id
            await client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name="document_id",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

            # Index for chunk_id
            await client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name="chunk_id",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

            # Index for created_at - use KEYWORD as DATETIME may not be available in all Qdrant versions
            await client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name="created_at",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

            # Index for tags
            await client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name="tags",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

            # Index for classification
            await client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name="classification",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

            logger.info(f"Created payload indexes for collection {self.config.collection_name}")
        except Exception as e:
            logger.warning(
                f"Failed to create one or more payload indexes. Last error: {e!s}",
                exc_info=True,
            )
            # Continue without indexes - they're not critical

    async def store_vectors(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
        batch_size: int = 100,
    ) -> list[str]:
        """
        Store vectors in the Qdrant collection.

        Args:
            vectors: List of vectors to store
            payloads: List of payloads to associate with vectors
            ids: Optional list of IDs for vectors (generated if not provided)
            batch_size: Batch size for storage operations

        Returns:
            List of IDs for the stored vectors
        """
        client = await self._get_client()
        if not vectors:
            logger.warning("No vectors provided to store")
            return []

        if len(vectors) != len(payloads):
            raise ValueError(
                f"Number of vectors ({len(vectors)}) must match number of payloads ({len(payloads)})"
            )

        # Generate IDs if not provided
        final_ids: list[str] = []
        if ids is None:
            final_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        elif len(ids) != len(vectors):
            raise ValueError(
                f"Number of IDs ({len(ids)}) must match number of vectors ({len(vectors)})"
            )
        else:
            final_ids = ids

        try:
            # Process in batches
            for i in range(0, len(vectors), batch_size):
                batch_end = min(i + batch_size, len(vectors))
                batch_vectors = vectors[i:batch_end]
                batch_payloads = payloads[i:batch_end]
                batch_final_ids = final_ids[i:batch_end]

                # Add timestamp to payloads
                timestamp = datetime.now(UTC)
                for payload in batch_payloads:
                    if "created_at" not in payload:
                        payload["created_at"] = timestamp.isoformat()

                # Convert IDs to UUIDs or keep as strings if Qdrant client handles it
                # Qdrant PointStruct id can be str, int, or UUID. Let's assume string IDs are fine.

                points = [
                    qdrant_models.PointStruct(
                        id=point_id,  # type: ignore
                        vector=vector,
                        payload=payload,
                    )
                    for point_id, vector, payload in zip(
                        batch_final_ids, batch_vectors, batch_payloads, strict=False
                    )
                ]

                # Store vectors
                await client.upsert(
                    collection_name=self.config.collection_name,
                    points=points,  # type: ignore
                )

                logger.debug(f"Stored batch of {len(batch_vectors)} vectors")

            logger.info(f"Successfully stored {len(vectors)} vectors")
            return final_ids

        except Exception as e:
            logger.error(f"Failed to store vectors: {e!s}", exc_info=True)
            raise

    async def search_similar(
        self,
        query_vector: list[float],
        filter_params: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
        score_threshold: float | None = None,
        hnsw_ef: int | None = None,  # Added for query-time ef tuning
    ) -> list[QdrantSearchResult]:
        """
        Search for vectors similar to the query vector.

        Args:
            query_vector: Query vector to search for
            filter_params: Optional filter parameters
            limit: Maximum number of results to return (uses default if not provided)
            offset: Offset for pagination
            score_threshold: Minimum similarity score threshold
            hnsw_ef: Optional HNSW ef parameter for search-time tuning

        Returns:
            List of search results
        """
        client = await self._get_client()
        try:
            # Convert filter params to Qdrant filter
            qdrant_filter = self._build_filter(filter_params) if filter_params else None

            # Use provided limit or default from config
            actual_limit = limit if limit is not None else self.config.default_limit

            # Prepare search parameters for client.query_points (qdrant-client 1.10+)
            search_kwargs: dict[str, Any] = {
                "collection_name": self.config.collection_name,
                "query": query_vector,
                "query_filter": qdrant_filter,
                "limit": actual_limit,
                "offset": offset,
                "with_payload": True,  # type: ignore
                "score_threshold": score_threshold,
            }

            # Add hnsw_ef if provided, otherwise Qdrant uses collection's default
            search_params_qdrant: qdrant_models.SearchParams | None = None
            if hnsw_ef is not None:
                search_params_qdrant = qdrant_models.SearchParams(hnsw_ef=hnsw_ef)
            elif self.config.ef_search is not None:
                search_params_qdrant = qdrant_models.SearchParams(hnsw_ef=self.config.ef_search)

            if search_params_qdrant:
                search_kwargs["search_params"] = search_params_qdrant

            # Execute search using query_points (replaces deprecated search method)
            search_response = await client.query_points(**search_kwargs)  # type: ignore

            # Convert to QdrantSearchResult objects
            results = []
            for hit in search_response.points:  # type: ignore
                # Extract document_id and chunk_id from payload
                document_id = hit.payload.get("document_id") if hit.payload else None  # type: ignore
                chunk_id = hit.payload.get("chunk_id") if hit.payload else None  # type: ignore

                # Create result object
                result = QdrantSearchResult(
                    id=str(hit.id),  # type: ignore
                    score=hit.score,  # type: ignore
                    payload=hit.payload or {},  # type: ignore
                    document_id=document_id,
                    chunk_id=chunk_id,
                )
                results.append(result)

            logger.info(f"Found {len(results)} similar vectors")
            return results

        except Exception as e:
            logger.error(f"Failed to search similar vectors: {e!s}", exc_info=True)
            raise

    async def search_similar_in_collection(
        self,
        collection_name: str,
        query_vector: list[float],
        filter_params: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
        score_threshold: float | None = None,
    ) -> list[QdrantSearchResult]:
        """
        Search for vectors similar to the query vector in a specific collection.

        Args:
            collection_name: Target Qdrant collection name
            query_vector: Query vector to search for
            filter_params: Optional filter parameters
            limit: Maximum number of results to return
            offset: Offset for pagination
            score_threshold: Minimum similarity score threshold

        Returns:
            List of search results
        """
        client = await self._get_client()
        try:
            qdrant_filter = self._build_filter(filter_params) if filter_params else None

            actual_limit = limit if limit is not None else self.config.default_limit

            search_kwargs: dict[str, Any] = {
                "collection_name": collection_name,
                "query": query_vector,
                "query_filter": qdrant_filter,
                "limit": actual_limit,
                "offset": offset,
                "with_payload": True,  # type: ignore
                "score_threshold": score_threshold,
            }

            if self.config.ef_search is not None:
                search_kwargs["search_params"] = qdrant_models.SearchParams(
                    hnsw_ef=self.config.ef_search
                )

            search_response = await client.query_points(**search_kwargs)  # type: ignore

            results: list[QdrantSearchResult] = []
            for hit in search_response.points:  # type: ignore
                document_id = hit.payload.get("document_id") if hit.payload else None  # type: ignore
                chunk_id = hit.payload.get("chunk_id") if hit.payload else None  # type: ignore

                results.append(
                    QdrantSearchResult(
                        id=str(hit.id),  # type: ignore
                        score=hit.score,  # type: ignore
                        payload=hit.payload or {},  # type: ignore
                        document_id=document_id,
                        chunk_id=chunk_id,
                    )
                )

            logger.info(f"Found {len(results)} results in collection '{collection_name}'")
            return results

        except Exception as e:
            logger.error(
                f"Failed to search vectors in collection '{collection_name}': {e!s}",
                exc_info=True,
            )
            raise

    def _build_filter(self, filter_params: dict[str, Any]) -> qdrant_models.Filter:
        """
        Build a Qdrant filter from filter parameters.

        Args:
            filter_params: Filter parameters

        Returns:
            Qdrant filter
        """
        # Start with empty conditions list
        conditions: list[qdrant_models.Condition] = []

        # Process each filter parameter
        for key, value in filter_params.items():
            # Handle special case for date ranges
            if key.endswith("_from") and key[:-5] + "_to" in filter_params:
                base_key = key[:-5]
                from_value = value
                to_value = filter_params[base_key + "_to"]

                # Create range condition
                range_condition = qdrant_models.FieldCondition(
                    key=base_key,
                    range=qdrant_models.Range(  # type: ignore
                        gte=from_value,
                        lte=to_value,
                    ),
                )
                conditions.append(range_condition)  # type: ignore

            # Handle special case for date ranges (just continue if we've already processed this)
            elif key.endswith("_to") and key[:-3] + "_from" in filter_params:
                continue

            # Handle lists (match any)
            elif isinstance(value, list):
                match_any = qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchAny(any=value),  # type: ignore
                )
                conditions.append(match_any)  # type: ignore

            # Handle simple match
            else:
                match = qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchValue(value=value),  # type: ignore
                )
                conditions.append(match)  # type: ignore

        # Combine all conditions with AND
        return qdrant_models.Filter(  # type: ignore
            must=conditions,  # type: ignore
        )

    async def delete_by_filter(self, filter_params: dict[str, Any]) -> int:
        """
        Delete vectors matching the filter.

        Args:
            filter_params: Filter parameters

        Returns:
            Number of deleted vectors
        """
        client = await self._get_client()
        try:
            # Convert filter params to Qdrant filter
            qdrant_filter = self._build_filter(filter_params)

            # Execute deletion
            result = await client.delete(
                collection_name=self.config.collection_name,
                points_selector=qdrant_models.FilterSelector(  # type: ignore
                    filter=qdrant_filter,
                ),
            )

            # Return number of deleted vectors
            # The structure of the result object might vary. Adapt as needed.
            # Assuming result is an UpdateResult or similar with an 'operation_id' and 'status'
            # For async client, delete might not directly return count.
            # We might need to infer success from status or lack of exception.
            # For now, let's assume if it doesn't raise, it's "successful" in submitting.
            # A more robust way would be to check result.status if available.
            logger.info(f"Delete by filter operation submitted. Result: {result}")
            return (
                -1
            )  # Placeholder, as direct count of deleted items isn't always returned by async delete

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e!s}", exc_info=True)
            raise

    async def delete_by_ids(self, ids: list[str]) -> int:
        """
        Delete vectors by IDs.

        Args:
            ids: List of vector IDs to delete

        Returns:
            Number of deleted vectors (or an indicator of submission success)
        """
        client = await self._get_client()
        if not ids:
            logger.warning("No IDs provided for deletion")
            return 0

        # Qdrant PointId can be str, int, or UUID. Assuming string IDs are used.
        point_ids_to_delete: list[str | int | uuid.UUID] = [str(id_val) for id_val in ids]

        try:
            # Execute deletion
            result = await client.delete(
                collection_name=self.config.collection_name,
                points_selector=qdrant_models.PointIdsList(  # type: ignore
                    points=point_ids_to_delete,  # type: ignore
                ),
            )
            logger.info(f"Delete by IDs operation submitted. Result: {result}")
            return -1  # Placeholder, similar to delete_by_filter

        except Exception as e:
            logger.error(f"Failed to delete vectors by IDs: {e!s}", exc_info=True)
            raise

    async def delete_by_document_id(self, document_id: str) -> int:
        """
        Delete all vectors associated with a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted vectors (or an indicator of submission success)
        """
        try:
            # Delete vectors with matching document_id
            return await self.delete_by_filter({"document_id": document_id})

        except Exception as e:
            logger.error(
                f"Failed to delete vectors for document {document_id}: {e!s}",
                exc_info=True,
            )
            raise

    async def count_vectors(self, filter_params: dict[str, Any] | None = None) -> int:
        """
        Count vectors matching the filter.

        Args:
            filter_params: Optional filter parameters

        Returns:
            Number of matching vectors
        """
        client = await self._get_client()
        try:
            # Convert filter params to Qdrant filter
            qdrant_filter = self._build_filter(filter_params) if filter_params else None

            # Execute count
            result = await client.count(
                collection_name=self.config.collection_name,
                count_filter=qdrant_filter,  # type: ignore
            )

            # Return count
            count = result.count
            logger.debug(f"Counted {count} vectors matching filter")
            return count

        except Exception as e:
            logger.error(f"Failed to count vectors: {e!s}", exc_info=True)
            raise

    async def health_check(self) -> bool:
        """
        Check if the Qdrant collection is healthy.

        Returns:
            True if the collection is healthy, False otherwise
        """
        client = await self._get_client()
        try:
            # Get collection info
            await client.get_collection(self.config.collection_name)

            # Simple query test using query_points (qdrant-client 1.10+)
            await client.query_points(
                collection_name=self.config.collection_name,
                query=[0.0] * self.config.vector_size,  # type: ignore
                limit=1,
            )

            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e!s}")
            return False

    async def optimize_index(self) -> bool:
        """
        Trigger index optimization for the collection.

        This can improve search performance but may take time for large collections.

        Returns:
            True if optimization was triggered successfully
        """
        client = await self._get_client()
        try:
            await client.update_collection(
                collection_name=self.config.collection_name,
                optimizers_config=qdrant_models.OptimizersConfigDiff(  # type: ignore
                    indexing_threshold=0  # Force optimization
                ),
            )

            logger.info(f"Optimization triggered for collection {self.config.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to trigger optimization: {e!s}", exc_info=True)
            return False

    async def close(self) -> None:  # Changed to async
        """Close the Qdrant client and release resources."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("AsyncQdrantClient session closed.")
        else:
            logger.debug("QdrantRepository client was not initialized or already closed.")

    async def delete_vectors_by_document_id(self, document_id: str) -> None:
        """Delete all vectors in Qdrant for a given document_id."""
        logger.info(f"Calling delete_by_document_id for document_id={document_id}")
        await self.delete_by_document_id(document_id)


# Factory function to create repository from environment variables
async def create_vector_repository_from_env() -> QdrantRepository:  # Changed to async
    """
    Create a Vector Repository using environment variables.

    Environment variables:
        QDRANT_URL: URL of the Qdrant server
        QDRANT_PORT: Port of the Qdrant server (optional)
        QDRANT_API_KEY: API key for Qdrant authentication (optional)
        QDRANT_PREFER_GRPC: Whether to prefer gRPC over HTTP (optional)
        QDRANT_TIMEOUT: Timeout for Qdrant operations in seconds (optional)
        QDRANT_COLLECTION: Name of the main collection (optional)
        QDRANT_VECTOR_SIZE: Size of embedding vectors (optional)
        QDRANT_DISTANCE: Distance function for similarity search (optional)

    Returns:
        Configured QdrantRepository instance
    """
    qdrant_settings = load_qdrant_config()

    config = VectorRepositoryConfig(
        url=qdrant_settings.get_url(),
        port=qdrant_settings.port,
        api_key=qdrant_settings.api_key,
        prefer_grpc=qdrant_settings.prefer_grpc,
        timeout=qdrant_settings.timeout,
        collection_name=qdrant_settings.collection_name,
        vector_size=qdrant_settings.vector_size,
        distance=qdrant_settings.distance,
        m=qdrant_settings.m,
        ef_construct=qdrant_settings.ef_construct,
        ef_search=qdrant_settings.ef_search,
        default_limit=qdrant_settings.default_limit,
        default_offset=qdrant_settings.default_offset,
        indexing_threshold=qdrant_settings.indexing_threshold,
    )

    return QdrantRepository(config)


# FastAPI dependency for injection
_repository_instance: QdrantRepository | None = None


async def get_vector_repository() -> QdrantRepository:
    """
    Get or create a Vector Repository instance.

    This function is designed to be used as a FastAPI dependency.
    It will create a singleton repository instance on first call and
    return the same instance for subsequent calls.

    Returns:
        QdrantRepository instance
    """
    global _repository_instance

    if _repository_instance is None:
        _repository_instance = await create_vector_repository_from_env()  # await the factory
        # Initialize collection
        await _repository_instance.initialize_collection()

    return _repository_instance


# Cleanup function to close repository on application shutdown
async def close_vector_repository() -> None:  # No change, already async
    """Close the global Vector Repository instance on application shutdown."""
    global _repository_instance

    if _repository_instance is not None:
        await _repository_instance.close()  # await the close
        _repository_instance = None
        logger.info("Closed global Vector Repository instance")
