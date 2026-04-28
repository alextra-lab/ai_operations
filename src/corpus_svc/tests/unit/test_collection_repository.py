"""
Unit tests for collection repository.

Tests collection CRUD operations, validation logic, and embedding model
consistency enforcement.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.corpus_svc.app.db.models import Collection
from src.corpus_svc.app.repositories.collection_repository import CollectionRepository
from src.corpus_svc.app.schemas.collections import CollectionCreate, CollectionUpdate


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def collection_repo(mock_session):
    """Create collection repository with mock session."""
    return CollectionRepository(mock_session)


@pytest.fixture
def sample_collection():
    """Create sample collection for testing."""
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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        document_count=0,
    )


class TestCollectionRepository:
    """Test suite for CollectionRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, collection_repo, mock_session, sample_collection):
        """Test getting collection by ID when it exists."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute
        result = await collection_repo.get_by_id(sample_collection.id)

        # Assert
        assert result == sample_collection
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, collection_repo, mock_session):
        """Test getting collection by ID when it doesn't exist."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await collection_repo.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name(self, collection_repo, mock_session, sample_collection):
        """Test getting collection by name."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute
        result = await collection_repo.get_by_name("test_collection")

        # Assert
        assert result == sample_collection

    @pytest.mark.asyncio
    async def test_get_default_collection(self, collection_repo, mock_session, sample_collection):
        """Test getting default collection."""
        sample_collection.is_default = True

        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute
        result = await collection_repo.get_default_collection()

        # Assert
        assert result == sample_collection
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_create_collection(self, collection_repo, mock_session):
        """Test creating a new collection."""
        # Setup
        collection_data = CollectionCreate.model_validate(
            {
                "name": "new_collection",
                "description": "New test collection",
                "embedding_model": "text-embedding-3-small",
                "embedding_provider": "openai",
                "embedding_dimensions": 1536,
                "preflight_sample_tokens": 10000,
                "auto_chunk_enabled": True,
                "preflight_strategies": ["sentence_paragraph", "fixed_token"],
            }
        )

        # Mock get_by_name to return None (no existing collection)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        await collection_repo.create_collection(collection_data, "testuser")

        # Assert
        assert mock_session.add.called
        assert mock_session.flush.called
        assert mock_session.refresh.called

    @pytest.mark.asyncio
    async def test_create_collection_duplicate_name(
        self, collection_repo, mock_session, sample_collection
    ):
        """Test creating collection with duplicate name fails."""
        # Setup
        collection_data = CollectionCreate.model_validate(
            {
                "name": "test_collection",  # Same as sample_collection
                "description": "Duplicate",
                "embedding_model": "text-embedding-3-small",
                "embedding_provider": "openai",
                "embedding_dimensions": 1536,
                "preflight_sample_tokens": 10000,
                "auto_chunk_enabled": True,
                "preflight_strategies": ["sentence_paragraph"],
            }
        )

        # Mock get_by_name to return existing collection
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute and assert raises
        with pytest.raises(ValueError, match="already exists"):
            await collection_repo.create_collection(collection_data, "testuser")

    @pytest.mark.asyncio
    async def test_update_collection(self, collection_repo, mock_session, sample_collection):
        """Test updating collection."""
        # Setup mocks
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_get_result

        update_data = CollectionUpdate(description="Updated description", is_active=False)

        # Execute
        updated_collection = await collection_repo.update_collection(
            sample_collection.id, update_data
        )

        # Assert
        assert updated_collection is not None
        assert mock_session.flush.called
        assert mock_session.refresh.called

    @pytest.mark.asyncio
    async def test_delete_collection_success(
        self, collection_repo, mock_session, sample_collection
    ):
        """Test deleting empty collection."""
        # Setup - collection with no documents
        sample_collection.document_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute
        result = await collection_repo.delete_collection(sample_collection.id)

        # Assert
        assert result is True
        assert mock_session.delete.called

    @pytest.mark.asyncio
    async def test_delete_collection_with_documents(
        self, collection_repo, mock_session, sample_collection
    ):
        """Test deleting collection with documents fails."""
        # Setup - collection with documents
        sample_collection.document_count = 5

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute and assert raises
        with pytest.raises(ValueError, match="with 5 documents"):
            await collection_repo.delete_collection(sample_collection.id)

    @pytest.mark.asyncio
    async def test_delete_system_managed_collection(
        self, collection_repo, mock_session, sample_collection
    ):
        """Test deleting system-managed collection fails."""
        # Setup - system-managed collection
        sample_collection.is_system_managed = True
        sample_collection.document_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute and assert raises
        with pytest.raises(ValueError, match="system-managed"):
            await collection_repo.delete_collection(sample_collection.id)

    def test_generate_qdrant_name(self):
        """Test Qdrant collection name generation."""
        name = CollectionRepository._generate_qdrant_name(
            "threat_intel", "text-embedding-3-small", 1536
        )

        # Assert format
        assert name.startswith("fc_threat_intel_")
        assert len(name.split("_")) == 4  # fc_threat_intel_<hash>
        assert len(name.split("_")[3]) == 8  # 8-character hash

    def test_generate_qdrant_name_consistent(self):
        """Test Qdrant name generation is consistent."""
        name1 = CollectionRepository._generate_qdrant_name("test", "model-a", 384)
        name2 = CollectionRepository._generate_qdrant_name("test", "model-a", 384)

        # Same inputs should produce same output
        assert name1 == name2

    def test_generate_qdrant_name_different_models(self):
        """Test different embedding models produce different Qdrant names."""
        name1 = CollectionRepository._generate_qdrant_name("test", "model-a", 384)
        name2 = CollectionRepository._generate_qdrant_name("test", "model-b", 384)

        # Different models should produce different names
        assert name1 != name2

    @pytest.mark.asyncio
    async def test_validate_collections_compatible_single(
        self, collection_repo, mock_session, sample_collection
    ):
        """Test validating single collection."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_collection
        mock_session.execute.return_value = mock_result

        # Execute
        is_valid, error = await collection_repo.validate_collections_compatible(
            [sample_collection.id]
        )

        # Assert
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_collections_compatible_multiple_same_model(
        self, collection_repo, mock_session
    ):
        """Test validating multiple collections with same embedding model."""
        # Setup - two collections with same model
        col1 = Collection(
            id=uuid4(),
            name="col1",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            is_active=True,
            qdrant_collection_name="fc_col1_abc",
            embedding_provider="openai",
            created_by="test",
            document_count=0,
        )
        col2 = Collection(
            id=uuid4(),
            name="col2",
            embedding_model="text-embedding-3-small",  # Same model
            embedding_dimensions=1536,
            is_active=True,
            qdrant_collection_name="fc_col2_abc",
            embedding_provider="openai",
            created_by="test",
            document_count=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [col1, col2]
        mock_session.execute.return_value = mock_result

        # Execute
        is_valid, error = await collection_repo.validate_collections_compatible([col1.id, col2.id])

        # Assert
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_collections_incompatible_different_models(
        self, collection_repo, mock_session
    ):
        """Test validating collections with different embedding models fails."""
        # Setup - two collections with different models
        col1 = Collection(
            id=uuid4(),
            name="col1",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            is_active=True,
            qdrant_collection_name="fc_col1_abc",
            embedding_provider="openai",
            created_by="test",
            document_count=0,
        )
        col2 = Collection(
            id=uuid4(),
            name="col2",
            embedding_model="all-minilm-l6-v2",  # Different model
            embedding_dimensions=384,
            is_active=True,
            qdrant_collection_name="fc_col2_xyz",
            embedding_provider="local",
            created_by="test",
            document_count=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [col1, col2]
        mock_session.execute.return_value = mock_result

        # Execute
        is_valid, error = await collection_repo.validate_collections_compatible([col1.id, col2.id])

        # Assert
        assert is_valid is False
        assert "different embedding models" in error
