"""
Unit tests for collection router endpoints.

Tests HTTP routing, request/response handling, and URL structure
for collection management endpoints.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from shared.auth import TokenPayload, get_current_user
from src.corpus_svc.app.db.models import Collection
from src.corpus_svc.app.main import app
from src.corpus_svc.app.routers import collections

client = TestClient(app)

VALID_UUID = str(uuid4())


def make_token_payload(sub: str, roles: list[str]) -> TokenPayload:
    """Create TokenPayload with all required fields for testing."""
    now = int(time.time())
    return TokenPayload(
        sub=sub,
        user_id=VALID_UUID,
        roles=roles,
        exp=now + 3600,  # 1 hour from now
        iat=now,
        iss="test-issuer",
        token_type="access",
    )


def make_admin_payload():
    """Create admin TokenPayload for testing."""
    return make_token_payload("admin", ["admin"])


def make_corpus_admin_payload():
    """Create corpus_admin TokenPayload for testing."""
    return make_token_payload("corpus_admin", ["corpus_admin"])


def make_regular_user_payload():
    """Create regular user TokenPayload for testing."""
    return make_token_payload("user", ["user"])


@pytest.fixture
def mock_collection():
    """Create mock collection for testing."""
    from datetime import UTC, datetime

    return Collection(
        id=uuid4(),
        name="test_collection",
        description="Test collection",
        embedding_model="text-embedding-3-small",
        embedding_provider="openai",
        embedding_dimensions=1536,
        qdrant_collection_name="fc_test_collection_abc12345",
        is_default=False,
        is_active=True,
        is_system_managed=False,
        created_by="testuser",
        document_count=0,
        preflight_sample_tokens=10000,
        preflight_strategies=["sentence_paragraph", "fixed_token"],
        auto_chunk_enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def override_dependencies():
    """Override app dependencies for testing."""
    mock_session = AsyncMock()

    app.dependency_overrides.clear()
    app.dependency_overrides[collections.get_db_session] = lambda: mock_session

    yield

    app.dependency_overrides.clear()


class TestCollectionRouterURLs:
    """Test suite for collection router URL structure and redirects."""

    def test_list_collections_with_trailing_slash(self, mock_collection):
        """Test that listing collections works with trailing slash."""
        mock_repo = MagicMock()
        mock_repo.list_collections = AsyncMock(return_value=([mock_collection], 1))

        # Override auth dependency
        app.dependency_overrides[get_current_user] = make_admin_payload

        with patch(
            "src.corpus_svc.app.routers.collections.CollectionRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/admin/collections/")

        assert response.status_code == 200
        data = response.json()
        assert "collections" in data
        assert "total" in data

    def test_list_collections_without_trailing_slash_redirects(self):
        """Test that listing collections without trailing slash redirects (307)."""
        app.dependency_overrides[get_current_user] = make_admin_payload

        response = client.get("/api/v1/admin/collections", follow_redirects=False)

        # FastAPI redirects to URL with trailing slash
        assert response.status_code == 307
        # TestClient returns full URL with testserver
        assert response.headers["location"].endswith("/api/v1/admin/collections/")

    def test_create_collection_with_trailing_slash(self, mock_collection):
        """Test that creating collection works with trailing slash."""
        mock_repo = MagicMock()
        mock_repo.create_collection = AsyncMock(return_value=mock_collection)
        mock_repo.get_by_name = AsyncMock(return_value=None)

        collection_data = {
            "name": "test_collection",
            "description": "Test collection",
            "embedding_model": "text-embedding-3-small",
            "embedding_provider": "openai",
            "embedding_dimensions": 1536,
        }

        # Override auth dependency
        app.dependency_overrides[get_current_user] = make_admin_payload

        # Mock the model registry check - needs to be awaitable
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("openai", 1536)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        app.dependency_overrides[collections.get_db_session] = lambda: mock_session

        # Mock Qdrant repository to avoid external connection
        mock_vector_repo = MagicMock()
        mock_vector_repo.initialize_collection = AsyncMock(return_value=True)

        with (
            patch(
                "src.corpus_svc.app.routers.collections.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.corpus_svc.app.repositories.vector_repository.QdrantRepository",
                return_value=mock_vector_repo,
            ),
            patch(
                "src.corpus_svc.app.repositories.vector_repository.VectorRepositoryConfig",
            ),
        ):
            response = client.post("/api/v1/admin/collections/", json=collection_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_collection"

    def test_create_collection_without_trailing_slash_redirects(self):
        """Test that creating collection without trailing slash causes redirect."""
        collection_data = {
            "name": "test_collection",
            "description": "Test collection",
            "embedding_model": "text-embedding-3-small",
            "embedding_provider": "openai",
            "embedding_dimensions": 1536,
        }

        app.dependency_overrides[get_current_user] = make_admin_payload

        response = client.post(
            "/api/v1/admin/collections", json=collection_data, follow_redirects=False
        )

        # POST requests get 307 redirect but body is lost
        assert response.status_code == 307


class TestCollectionRouterPermissions:
    """Test suite for collection router permission checks."""

    def test_list_collections_admin_allowed(self, mock_collection):
        """Test that admin can list collections."""
        mock_repo = MagicMock()
        mock_repo.list_collections = AsyncMock(return_value=([mock_collection], 1))

        app.dependency_overrides[get_current_user] = make_admin_payload

        with patch(
            "src.corpus_svc.app.routers.collections.CollectionRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/admin/collections/")

        assert response.status_code == 200

    def test_list_collections_corpus_admin_allowed(self, mock_collection):
        """Test that corpus_admin can list collections."""
        mock_repo = MagicMock()
        mock_repo.list_collections = AsyncMock(return_value=([mock_collection], 1))

        app.dependency_overrides[get_current_user] = make_corpus_admin_payload

        with patch(
            "src.corpus_svc.app.routers.collections.CollectionRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/admin/collections/")

        assert response.status_code == 200

    def test_list_collections_regular_user_forbidden(self):
        """Test that regular user cannot list collections."""
        app.dependency_overrides[get_current_user] = make_regular_user_payload

        response = client.get("/api/v1/admin/collections/")

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestCollectionRouterValidation:
    """Test suite for collection router input validation."""

    def test_create_collection_invalid_name(self):
        """Test that creating collection with reserved name fails."""
        collection_data = {
            "name": "system",  # Reserved name (see validator in schema)
            "description": "Test collection",
            "embedding_model": "text-embedding-3-small",
            "embedding_provider": "openai",
            "embedding_dimensions": 1536,
        }

        app.dependency_overrides[get_current_user] = make_admin_payload

        response = client.post("/api/v1/admin/collections/", json=collection_data)

        assert response.status_code == 422  # Validation error

    def test_create_collection_missing_required_fields(self):
        """Test that creating collection without required fields fails."""
        collection_data = {
            "name": "test_collection",
            # Missing embedding_model, embedding_provider, embedding_dimensions
        }

        app.dependency_overrides[get_current_user] = make_admin_payload

        response = client.post("/api/v1/admin/collections/", json=collection_data)

        assert response.status_code == 422  # Validation error
