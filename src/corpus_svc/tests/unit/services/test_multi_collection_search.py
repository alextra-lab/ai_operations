from typing import Any

import pytest

from src.corpus_svc.app.services.query_service import QueryService


class DummyEmbedding:
    def __init__(self, vec: list[float]):
        self.embedding = vec


class DummyEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None,
        provider: str | None = None,
        auth_token: str | None = None,
    ):  # type: ignore[unused-argument]
        self.calls.append({"texts": texts, "model": model, "provider": provider})
        return [DummyEmbedding([0.1, 0.2, 0.3])]


class DummyVectorRepo:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def search_similar_in_collection(
        self,
        collection_name: str,
        query_vector: list[float],  # type: ignore[unused-argument]
        filter_params: dict[str, Any] | None = None,  # type: ignore[unused-argument]
        limit: int | None = None,
        offset: int = 0,  # type: ignore[unused-argument]
        score_threshold: float | None = None,  # type: ignore[unused-argument]
    ):
        self.calls.append({"collection": collection_name, "limit": limit})
        # Return minimal structures resembling QdrantSearchResult
        return [
            type(
                "Hit",
                (),
                {
                    "score": 0.9,
                    "payload": {
                        "document_id": "00000000-0000-0000-0000-000000000001",
                        "chunk_id": "00000000-0000-0000-0000-000000000011",
                        "text": "alpha",
                    },
                    "id": "1",
                },
            )
        ]

    async def search_similar(self, **kwargs):  # type: ignore[unused-argument]
        # Fallback single-collection
        return [
            type(
                "Hit",
                (),
                {
                    "score": 0.8,
                    "payload": {
                        "document_id": "00000000-0000-0000-0000-000000000002",
                        "chunk_id": "00000000-0000-0000-0000-000000000022",
                        "text": "beta",
                    },
                    "id": "2",
                },
            )
        ]


class DummyDoc:
    def __init__(self) -> None:
        self.title = "Doc"
        self.source = "test"
        self.author = "author"
        self.metadata_: dict[str, object] = {}
        self.file_type = "pdf"
        self.classification = None
        self.created_at = None


class DummyDocRepo:
    async def get_document_by_id(self, _):
        return DummyDoc()


class DummyUsageRepo:
    async def record_retrieval(self, **kwargs):  # type: ignore[unused-argument]
        return None


class DummyCollection:
    """Mock collection object for testing."""

    def __init__(self, name: str, qdrant_name: str | None = None) -> None:
        self.id = "00000000-0000-0000-0000-000000000001"
        self.name = name
        self.qdrant_collection_name = qdrant_name or f"fc_{name}_abcd1234"
        self.embedding_model = "text-embedding-3-small"
        self.embedding_provider = "openai"
        self.embedding_dimensions = 1536
        self.is_active = True


class DummyCollectionRepo:
    """Mock collection repository for testing multi-collection search."""

    def __init__(self) -> None:
        self.collections: dict[str, DummyCollection] = {
            "security_docs": DummyCollection("security_docs", "fc_security_docs_d40a039f"),
            "default": DummyCollection("default", "documents_test"),
        }

    async def get_by_id(self, collection_id):  # type: ignore[unused-argument]
        return DummyCollection("default")

    async def get_by_name(self, name: str):
        # Return a mock collection matching the requested name
        return self.collections.get(name, DummyCollection(name))

    async def validate_collections_compatible(self, collection_ids):  # type: ignore[unused-argument]
        return True, None


@pytest.mark.asyncio
async def test_multi_collection_merges_and_limits():
    """Test that multi-collection search merges results and applies limits correctly."""
    vector = DummyVectorRepo()
    embedding_client = DummyEmbeddingClient()
    collection_repo = DummyCollectionRepo()
    service = QueryService(
        vector_repository=vector,  # type: ignore[arg-type]
        document_repository=DummyDocRepo(),  # type: ignore[arg-type]
        usage_stats_repository=DummyUsageRepo(),  # type: ignore[arg-type]
        embedding_client=embedding_client,  # type: ignore[arg-type]
        collection_repository=collection_repo,  # type: ignore[arg-type]
    )

    results = await service.perform_semantic_search(
        query_text="test",
        top_k=1,
        collection_names=["security_docs", "default"],
    )

    assert len(results) == 1
    # Ensure both collections were queried with expanded per-collection limit
    assert len(vector.calls) == 2
    assert all(call["limit"] == 2 for call in vector.calls)
    # Verify Qdrant collection names were used (not database names)
    assert vector.calls[0]["collection"] == "fc_security_docs_d40a039f"
    assert vector.calls[1]["collection"] == "documents_test"
    # Verify provider was passed to embedding client
    assert len(embedding_client.calls) == 1
    assert embedding_client.calls[0]["provider"] == "openai"
    assert embedding_client.calls[0]["model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_collection_name_resolution():
    """Test that database collection names are resolved to Qdrant collection names."""
    vector = DummyVectorRepo()
    embedding_client = DummyEmbeddingClient()
    collection_repo = DummyCollectionRepo()
    service = QueryService(
        vector_repository=vector,  # type: ignore[arg-type]
        document_repository=DummyDocRepo(),  # type: ignore[arg-type]
        usage_stats_repository=DummyUsageRepo(),  # type: ignore[arg-type]
        embedding_client=embedding_client,  # type: ignore[arg-type]
        collection_repository=collection_repo,  # type: ignore[arg-type]
    )

    await service.perform_semantic_search(
        query_text="test query",
        top_k=5,
        collection_names=["security_docs"],
    )

    # Verify Qdrant collection name was used, not database name
    assert len(vector.calls) == 1
    assert vector.calls[0]["collection"] == "fc_security_docs_d40a039f"
    assert vector.calls[0]["collection"] != "security_docs"


@pytest.mark.asyncio
async def test_provider_parameter_passed():
    """Test that provider parameter is resolved from collection and passed to embedding client."""
    vector = DummyVectorRepo()
    embedding_client = DummyEmbeddingClient()
    collection_repo = DummyCollectionRepo()
    service = QueryService(
        vector_repository=vector,  # type: ignore[arg-type]
        document_repository=DummyDocRepo(),  # type: ignore[arg-type]
        usage_stats_repository=DummyUsageRepo(),  # type: ignore[arg-type]
        embedding_client=embedding_client,  # type: ignore[arg-type]
        collection_repository=collection_repo,  # type: ignore[arg-type]
    )

    await service.perform_semantic_search(
        query_text="test query",
        top_k=5,
        collection_names=["security_docs"],
    )

    # Verify provider was passed to embedding client
    assert len(embedding_client.calls) == 1
    assert embedding_client.calls[0]["provider"] == "openai"
    assert embedding_client.calls[0]["model"] == "text-embedding-3-small"
