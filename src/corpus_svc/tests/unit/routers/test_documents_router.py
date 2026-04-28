import io
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.corpus_svc.app.main import app
from src.corpus_svc.app.routers import documents

client = TestClient(app)

VALID_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def override_dependencies():
    # Mock DB session as AsyncMock
    mock_session = AsyncMock()

    # Mock user
    def mock_get_user():
        return {"user_id": VALID_UUID}

    # Set dependency overrides
    app.dependency_overrides.clear()
    app.dependency_overrides[documents.get_db_session] = lambda: mock_session
    app.dependency_overrides[documents.get_current_user] = mock_get_user
    yield
    app.dependency_overrides.clear()


def test_upload_document_success():
    file_content = b"%PDF-1.4\n%Fake PDF\n"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {"title": "Test Doc", "process_async": "false"}

    # Mock collection for collection lookup
    mock_collection = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="default",
        embedding_model="text-embedding-3-small",
        embedding_provider="openai",
        embedding_dimensions=1536,
        preflight_sample_tokens=10000,
        preflight_strategies=None,
        auto_chunk_enabled=False,
    )
    mock_collection_repo = MagicMock()
    mock_collection_repo.get_by_name = AsyncMock(return_value=mock_collection)

    # Mock document repository
    mock_doc_repo = MagicMock()
    mock_doc_repo.get_document_by_checksum = AsyncMock(return_value=None)
    mock_doc = SimpleNamespace(id=uuid.uuid4())
    mock_doc_repo.create_document = AsyncMock(return_value=mock_doc)

    # Mock ingestion service
    mock_ingest_service = MagicMock()
    mock_ingest_service.process_document = AsyncMock(
        return_value=SimpleNamespace(state="completed", error=None)
    )

    with (
        patch("pdfplumber.open", autospec=True) as mock_pdf_open,
        patch(
            "src.corpus_svc.app.routers.documents.get_repositories",
            return_value=(mock_doc_repo, MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.repositories.collection_repository.CollectionRepository",
            return_value=mock_collection_repo,
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_embedding_client",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.routers.documents.get_ingest_service",
            new=AsyncMock(return_value=mock_ingest_service),
        ),
        patch(
            "src.corpus_svc.app.repositories.vector_repository.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
    ):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(extract_text=lambda: "dummy text")]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        response = client.post("/api/v1/documents/", files=files, data=data)
    assert response.status_code in (201, 202)
    assert "document_id" in response.json()


def test_get_document_by_id_success():
    doc_id = VALID_UUID
    mock_doc = SimpleNamespace(
        id=doc_id,
        title="Test Doc",
        source="Test Source",
        author="Test Author",
        created_at="2025-07-08T00:00:00Z",
        ingested_at="2025-07-08T00:00:00Z",
        ingested_by=VALID_UUID,
        original_file_name="test.pdf",
        file_type="pdf",
        file_checksum="abc123",
        file_size=1234,
        content_compressed=True,
        embedding_model="all-minilm-l6-v2",
        embedding_provider="openai",
        embedding_dimensions=384,
        num_chunks=1,
        avg_chunk_size_tokens=100,
        tags=[],
        classification="public",
        status="processed",
        error_message=None,
        metadata_={},
        updated_at="2025-07-08T00:00:00Z",
        uploaded_by=VALID_UUID,
        uploaded_at="2025-07-08T00:00:00Z",
        processed_at="2025-07-08T00:00:00Z",
    )
    with patch(
        "src.corpus_svc.app.repositories.document_repository.DocumentRepository.get_document_by_id",
        new=AsyncMock(return_value=mock_doc),
    ):
        response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["id"] == doc_id


def test_list_documents_success():
    docs = [
        SimpleNamespace(
            id=VALID_UUID,
            title="Doc 1",
            source="Source 1",
            author="Author 1",
            created_at="2025-07-08T00:00:00Z",
            ingested_at="2025-07-08T00:00:00Z",
            ingested_by=VALID_UUID,
            original_file_name="doc1.pdf",
            file_type="pdf",
            file_checksum="abc123",
            file_size=1234,
            content_compressed=True,
            embedding_model="all-minilm-l6-v2",
            embedding_provider="openai",
            embedding_dimensions=384,
            num_chunks=1,
            avg_chunk_size_tokens=100,
            tags=[],
            classification="public",
            status="processed",
            error_message=None,
            metadata_={},
            updated_at="2025-07-08T00:00:00Z",
            uploaded_by=VALID_UUID,
            uploaded_at="2025-07-08T00:00:00Z",
            processed_at="2025-07-08T00:00:00Z",
        )
    ]
    with patch(
        "src.corpus_svc.app.repositories.document_repository.DocumentRepository.search_documents",
        new=AsyncMock(return_value=docs),
    ):
        response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["id"] == VALID_UUID


def test_delete_document_success():
    doc_id = VALID_UUID
    # Mock document returned by get_document_by_id
    mock_doc = SimpleNamespace(
        id=doc_id,
        # Add any other required fields if needed by the endpoint
    )
    # Mock vector repo with async delete_vectors_by_document_id
    mock_vector_repo = MagicMock()
    mock_vector_repo.delete_vectors_by_document_id = AsyncMock(return_value=None)

    with (
        patch(
            "src.corpus_svc.app.repositories.document_repository.DocumentRepository.get_document_by_id",
            new=AsyncMock(return_value=mock_doc),
        ),
        patch(
            "src.corpus_svc.app.repositories.document_repository.DocumentRepository.update_document_status",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "src.corpus_svc.app.repositories.vector_repository.get_vector_repository",
            new=AsyncMock(return_value=mock_vector_repo),
        ),
    ):
        response = client.delete(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json().get("status") == "deleted"
    assert response.json().get("document_id") == doc_id


def test_update_document_success():
    doc_id = VALID_UUID
    update_data = {"title": "Updated Title"}
    updated_doc = SimpleNamespace(
        id=doc_id,
        title="Updated Title",
        source="Source 1",
        author="Author 1",
        created_at="2025-07-08T00:00:00Z",
        ingested_at="2025-07-08T00:00:00Z",
        ingested_by=VALID_UUID,
        original_file_name="doc1.pdf",
        file_type="pdf",
        file_checksum="abc123",
        file_size=1234,
        content_compressed=True,
        embedding_model="all-minilm-l6-v2",
        embedding_provider="openai",
        embedding_dimensions=384,
        num_chunks=1,
        avg_chunk_size_tokens=100,
        tags=[],
        classification="public",
        status="processed",
        error_message=None,
        metadata_={},
        updated_at="2025-07-08T00:00:00Z",
        uploaded_by=VALID_UUID,
        uploaded_at="2025-07-08T00:00:00Z",
        processed_at="2025-07-08T00:00:00Z",
    )
    with patch(
        "src.corpus_svc.app.repositories.document_repository.DocumentRepository.update_document",
        new=AsyncMock(return_value=updated_doc),
    ):
        response = client.patch(f"/api/v1/documents/{doc_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_get_document_by_id_not_found():
    doc_id = VALID_UUID
    with patch(
        "src.corpus_svc.app.repositories.document_repository.DocumentRepository.get_document_by_id",
        new=AsyncMock(return_value=None),
    ):
        response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 404


def test_upload_document_with_chunking_config():
    """Test document upload with chunking_config parameter."""
    import json

    file_content = b"%PDF-1.4\n%Fake PDF\n"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    chunking_config = {
        "strategy": "fixed_token",
        "chunk_size": 256,
        "chunk_overlap": 25,
    }
    data = {
        "title": "Test Doc",
        "process_async": "false",
        "chunking_config": json.dumps(chunking_config),
    }

    # Mock collection for collection lookup
    mock_collection = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="default",
        embedding_model="text-embedding-3-small",
        embedding_provider="openai",
        embedding_dimensions=1536,
        preflight_sample_tokens=10000,
        preflight_strategies=None,
        auto_chunk_enabled=False,
    )
    mock_collection_repo = MagicMock()
    mock_collection_repo.get_by_name = AsyncMock(return_value=mock_collection)

    # Mock document repository
    mock_doc_repo = MagicMock()
    mock_doc_repo.get_document_by_checksum = AsyncMock(return_value=None)
    mock_doc = SimpleNamespace(id=uuid.uuid4())
    mock_doc_repo.create_document = AsyncMock(return_value=mock_doc)

    # Mock ingestion service
    mock_ingest_service = MagicMock()
    mock_ingest_service.process_document = AsyncMock(
        return_value=SimpleNamespace(state="completed", error=None)
    )

    with (
        patch("pdfplumber.open", autospec=True) as mock_pdf_open,
        patch(
            "src.corpus_svc.app.routers.documents.get_repositories",
            return_value=(mock_doc_repo, MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.repositories.collection_repository.CollectionRepository",
            return_value=mock_collection_repo,
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_embedding_client",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.routers.documents.get_ingest_service",
            new=AsyncMock(return_value=mock_ingest_service),
        ),
        patch(
            "src.corpus_svc.app.repositories.vector_repository.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
    ):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(extract_text=lambda: "dummy text")]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        response = client.post("/api/v1/documents/", files=files, data=data)
    assert response.status_code in (201, 202)
    assert "document_id" in response.json()


def test_upload_document_with_auto_chunking():
    """Test document upload with auto chunking strategy."""
    import json

    file_content = b"%PDF-1.4\n%Fake PDF\n"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    chunking_config = {
        "strategy": "auto",
        "chunk_size": 512,
        "chunk_overlap": 50,
    }
    data = {
        "title": "Test Doc",
        "process_async": "false",
        "chunking_config": json.dumps(chunking_config),
    }

    # Mock collection for collection lookup (includes auto-chunking fields P4-DOC-07)
    mock_collection = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="default",
        embedding_model="text-embedding-3-small",
        embedding_provider="openai",
        embedding_dimensions=1536,
        preflight_sample_tokens=10000,
        auto_chunk_enabled=True,
        preflight_strategies=None,
    )
    mock_collection_repo = MagicMock()
    mock_collection_repo.get_by_name = AsyncMock(return_value=mock_collection)

    # Mock document repository
    mock_doc_repo = MagicMock()
    mock_doc_repo.get_document_by_checksum = AsyncMock(return_value=None)
    mock_doc = SimpleNamespace(id=uuid.uuid4())
    mock_doc_repo.create_document = AsyncMock(return_value=mock_doc)

    # Mock ingestion service
    mock_ingest_service = MagicMock()
    mock_ingest_service.process_document = AsyncMock(
        return_value=SimpleNamespace(state="completed", error=None)
    )

    # Mock preflight analysis result
    mock_preflight_report = SimpleNamespace(
        recommendation=SimpleNamespace(
            strategy=SimpleNamespace(value="heading_aware"),
            confidence=0.94,
            reasoning=["Document has clear hierarchical structure"],
        ),
        strategy_results=[
            SimpleNamespace(strategy=SimpleNamespace(value="heading_aware"), score=0.94),
            SimpleNamespace(strategy=SimpleNamespace(value="fixed_token"), score=0.65),
        ],
        sample_size_tokens=10000,
    )

    with (
        patch("pdfplumber.open", autospec=True) as mock_pdf_open,
        patch(
            "src.corpus_svc.app.routers.documents.get_repositories",
            return_value=(mock_doc_repo, MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.repositories.collection_repository.CollectionRepository",
            return_value=mock_collection_repo,
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_embedding_client",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.routers.documents.get_ingest_service",
            new=AsyncMock(return_value=mock_ingest_service),
        ),
        patch(
            "src.corpus_svc.app.repositories.vector_repository.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.services.preflight_service.PreflightAnalyzer.analyze",
            new=AsyncMock(return_value=mock_preflight_report),
        ),
    ):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(extract_text=lambda: "# Heading\n\nParagraph text.")]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        response = client.post("/api/v1/documents/", files=files, data=data)
    assert response.status_code in (201, 202)
    assert "document_id" in response.json()


def test_upload_document_with_invalid_chunking_config():
    """Test document upload with invalid chunking_config falls back to defaults."""
    file_content = b"%PDF-1.4\n%Fake PDF\n"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {
        "title": "Test Doc",
        "process_async": "false",
        "chunking_config": "invalid json",
    }

    # Mock collection for collection lookup
    mock_collection = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="default",
        embedding_model="text-embedding-3-small",
        embedding_provider="openai",
        embedding_dimensions=1536,
        preflight_sample_tokens=10000,
        preflight_strategies=None,
        auto_chunk_enabled=False,
    )
    mock_collection_repo = MagicMock()
    mock_collection_repo.get_by_name = AsyncMock(return_value=mock_collection)

    # Mock document repository
    mock_doc_repo = MagicMock()
    mock_doc_repo.get_document_by_checksum = AsyncMock(return_value=None)
    mock_doc = SimpleNamespace(id=uuid.uuid4())
    mock_doc_repo.create_document = AsyncMock(return_value=mock_doc)

    # Mock ingestion service
    mock_ingest_service = MagicMock()
    mock_ingest_service.process_document = AsyncMock(
        return_value=SimpleNamespace(state="completed", error=None)
    )

    with (
        patch("pdfplumber.open", autospec=True) as mock_pdf_open,
        patch(
            "src.corpus_svc.app.routers.documents.get_repositories",
            return_value=(mock_doc_repo, MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.repositories.collection_repository.CollectionRepository",
            return_value=mock_collection_repo,
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.services.ingestion_service.get_embedding_client",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "src.corpus_svc.app.routers.documents.get_ingest_service",
            new=AsyncMock(return_value=mock_ingest_service),
        ),
        patch(
            "src.corpus_svc.app.repositories.vector_repository.get_vector_repository",
            new=AsyncMock(return_value=MagicMock()),
        ),
    ):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(extract_text=lambda: "dummy text")]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        response = client.post("/api/v1/documents/", files=files, data=data)
    # Should still succeed with default chunking
    assert response.status_code in (201, 202)
    assert "document_id" in response.json()
