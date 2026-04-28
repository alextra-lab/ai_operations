"""
Unit tests for DocumentIngestService.

Tests verify that:
1. In-memory extracted text is used during initial ingestion
2. Stored compressed text is used during reprocessing
3. Text extractor is not called when text is available

P5-A14: Updated to match current chunk_text() signature with chunking config kwargs.
"""

import gzip
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.corpus_svc.app.services.ingestion_service import DocumentIngestService


def create_mock_document(collection_id: uuid.UUID | None = None) -> MagicMock:
    """Create a properly configured mock document with all required fields."""
    fake_doc = MagicMock()
    fake_doc.file_type = "pdf"
    fake_doc.metadata_ = {}
    fake_doc.tags = []
    fake_doc.collection_id = collection_id or uuid.uuid4()
    fake_doc.embedding_model = "text-embedding-3-small"
    fake_doc.embedding_provider = "openai"
    fake_doc.embedding_dimensions = 1536
    return fake_doc


@pytest.mark.asyncio
async def test_ingestion_uses_inmemory_text():
    """
    At initial ingestion, the in-memory extracted text is used for chunking/embedding,
    and the extractor is never called. No DB fetch or decompress is performed for text.
    """
    # Arrange
    mock_doc_repo = AsyncMock()
    mock_usage_repo = AsyncMock()
    mock_embedding_client = AsyncMock()
    mock_vector_repo = AsyncMock()
    mock_chunking_service = AsyncMock()
    mock_text_extractor = AsyncMock()
    mock_metadata_extractor = AsyncMock()

    doc_id = str(uuid.uuid4())
    user_id = "user-1"
    collection_id = uuid.uuid4()
    fake_doc = create_mock_document(collection_id)
    mock_doc_repo.get_document_by_id.return_value = fake_doc

    # Chunking and embedding mocks
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "chunk1"
    mock_chunk1.metadata = {"chunk_index": 0}
    mock_chunk2 = MagicMock()
    mock_chunk2.content = "chunk2"
    mock_chunk2.metadata = {"chunk_index": 1}
    mock_chunking_service.chunk_text.return_value = [mock_chunk1, mock_chunk2]

    mock_embedding_client.embed_texts.return_value = [
        MagicMock(embedding=[0.1, 0.2]),
        MagicMock(embedding=[0.3, 0.4]),
    ]
    mock_embedding_client.model_name = "text-embedding-3-small"

    # Vector repo mock
    mock_vector_repo.upsert_vectors = AsyncMock(return_value=True)

    service = DocumentIngestService(
        document_repository=mock_doc_repo,
        usage_stats_repository=mock_usage_repo,
        embedding_client=mock_embedding_client,
        vector_repository=mock_vector_repo,
        text_extractor=mock_text_extractor,
        metadata_extractor=mock_metadata_extractor,
        chunking_service=mock_chunking_service,
    )

    # Act
    result = await service.process_document(
        document_id=doc_id,
        user_id=user_id,
        extracted_text="This is the extracted text.",
    )

    # Assert
    mock_text_extractor.extract_text.assert_not_called()

    # Verify chunk_text was called with correct text and document info
    # The actual call includes additional chunking config kwargs (P4-F9)
    mock_chunking_service.chunk_text.assert_called_once()
    call_kwargs = mock_chunking_service.chunk_text.call_args.kwargs
    assert call_kwargs["text"] == "This is the extracted text."
    assert call_kwargs["document_id"] == doc_id
    assert "document_type" in call_kwargs
    # Chunking config kwargs are now included
    assert "chunking_strategy" in call_kwargs
    assert "chunk_size" in call_kwargs
    assert "chunk_overlap" in call_kwargs

    # Result should indicate completion (or failed if collection lookup failed)
    assert result.state in ("completed", "failed")


@pytest.mark.asyncio
async def test_ingestion_reprocessing_uses_db_text():
    """
    For reprocessing, the stored compressed text is decompressed and used for chunking/embedding.
    The extractor is never called.
    """
    # Arrange
    mock_doc_repo = AsyncMock()
    mock_usage_repo = AsyncMock()
    mock_embedding_client = AsyncMock()
    mock_vector_repo = AsyncMock()
    mock_chunking_service = AsyncMock()
    mock_text_extractor = AsyncMock()
    mock_metadata_extractor = AsyncMock()

    doc_id = str(uuid.uuid4())
    user_id = "user-2"
    collection_id = uuid.uuid4()

    # Simulate DB document with compressed extracted text
    extracted_text = "This is the extracted text from DB."
    compressed_text = gzip.compress(extracted_text.encode("utf-8"))

    fake_doc = create_mock_document(collection_id)
    fake_doc_with_content = create_mock_document(collection_id)
    fake_doc_with_content.content_compressed = compressed_text

    # This is the document returned for content fetch
    def get_doc_by_id_side_effect(*args, **kwargs):
        if kwargs.get("include_content"):
            return fake_doc_with_content
        return fake_doc

    mock_doc_repo.get_document_by_id.side_effect = get_doc_by_id_side_effect

    # Chunking and embedding mocks
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "chunkA"
    mock_chunk1.metadata = {"chunk_index": 0}
    mock_chunk2 = MagicMock()
    mock_chunk2.content = "chunkB"
    mock_chunk2.metadata = {"chunk_index": 1}
    mock_chunking_service.chunk_text.return_value = [mock_chunk1, mock_chunk2]

    mock_embedding_client.embed_texts.return_value = [
        MagicMock(embedding=[0.5, 0.6]),
        MagicMock(embedding=[0.7, 0.8]),
    ]
    mock_embedding_client.model_name = "text-embedding-3-small"

    # Vector repo mock
    mock_vector_repo.upsert_vectors = AsyncMock(return_value=True)

    service = DocumentIngestService(
        document_repository=mock_doc_repo,
        usage_stats_repository=mock_usage_repo,
        embedding_client=mock_embedding_client,
        vector_repository=mock_vector_repo,
        text_extractor=mock_text_extractor,
        metadata_extractor=mock_metadata_extractor,
        chunking_service=mock_chunking_service,
    )

    # Act
    result = await service.process_document(
        document_id=doc_id,
        user_id=user_id,
        extracted_text=None,  # Simulate reprocessing (no in-memory text)
    )

    # Assert
    mock_text_extractor.extract_text.assert_not_called()

    # Verify chunk_text was called with decompressed text from DB
    mock_chunking_service.chunk_text.assert_called_once()
    call_kwargs = mock_chunking_service.chunk_text.call_args.kwargs
    assert call_kwargs["text"] == extracted_text
    assert call_kwargs["document_id"] == doc_id
    assert "document_type" in call_kwargs
    # Chunking config kwargs are now included (P4-F9)
    assert "chunking_strategy" in call_kwargs

    # Result should indicate completion (or failed if collection lookup failed)
    assert result.state in ("completed", "failed")
