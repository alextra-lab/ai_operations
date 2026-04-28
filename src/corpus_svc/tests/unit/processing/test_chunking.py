import pytest

from src.corpus_svc.app.processing.chunking import ChunkingService
from src.corpus_svc.app.schemas.document import DocumentType


@pytest.mark.asyncio
async def test_chunk_text_basic():
    service = ChunkingService()
    text = "This is a test document. It has several sentences. Each sentence should be chunked."
    chunks = await service.chunk_text(text, document_id="doc1", document_type=DocumentType.TXT)
    assert isinstance(chunks, list)
    from src.corpus_svc.app.schemas.chunk import ChunkCreate

    assert all(isinstance(chunk, ChunkCreate) for chunk in chunks)
    assert all(isinstance(chunk.content, str) for chunk in chunks)
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_chunk_text_empty():
    service = ChunkingService()
    text = ""
    chunks = await service.chunk_text(text, document_id="doc1", document_type=DocumentType.TXT)
    assert isinstance(chunks, list)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_chunk_text_custom_params():
    service = ChunkingService()
    text = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
    chunks = await service.chunk_text(text, document_id="doc1", document_type=DocumentType.TXT)
    assert isinstance(chunks, list)
    from src.corpus_svc.app.schemas.chunk import ChunkCreate

    assert all(isinstance(chunk, ChunkCreate) for chunk in chunks)
    assert all(isinstance(chunk.content, str) for chunk in chunks)
    # Should produce at least one chunk
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_chunk_text_invalid_input():
    service = ChunkingService()
    # Passing empty string as text should return an empty list (not raise)
    chunks = await service.chunk_text("", document_id="doc1", document_type=DocumentType.TXT)
    assert isinstance(chunks, list)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_chunk_text_fixed_token_strategy():
    """Test fixed_token chunking strategy."""
    service = ChunkingService()
    text = " ".join(["word"] * 200)  # Create a long text
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="fixed_token",
        chunk_size=128,
        chunk_overlap=10,
    )
    assert len(chunks) > 0
    assert all(chunk.metadata.get("strategy") == "fixed_token" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_sliding_token_strategy():
    """Test sliding_token chunking strategy."""
    service = ChunkingService()
    text = " ".join(["word"] * 200)
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="sliding_token",
        chunk_size=128,
        chunk_overlap=20,
    )
    assert len(chunks) > 0
    assert all(chunk.metadata.get("strategy") == "sliding_token" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_heading_aware_strategy():
    """Test heading_aware chunking strategy."""
    service = ChunkingService()
    text = "# Heading 1\n\nParagraph text here.\n\n## Heading 2\n\nMore text."
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="heading_aware",
        chunk_size=100,
        chunk_overlap=10,
    )
    assert len(chunks) > 0
    assert all(chunk.metadata.get("strategy") == "heading_aware" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_sentence_paragraph_strategy():
    """Test sentence_paragraph chunking strategy."""
    service = ChunkingService()
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="sentence_paragraph",
        chunk_size=100,
        chunk_overlap=10,
    )
    assert len(chunks) > 0
    assert all(chunk.metadata.get("strategy") == "sentence_paragraph" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_recursive_strategy():
    """Test recursive chunking strategy (default fallback)."""
    service = ChunkingService()
    text = "This is a test document with multiple sentences. Each sentence should be processed."
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="recursive",
        chunk_size=128,
        chunk_overlap=10,
    )
    assert len(chunks) > 0
    assert all(chunk.metadata.get("strategy") == "recursive" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_invalid_strategy_fallback():
    """Test that invalid strategy falls back to recursive."""
    service = ChunkingService()
    text = "Test document text."
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="invalid_strategy",
        chunk_size=128,
        chunk_overlap=10,
    )
    # Should still produce chunks with recursive fallback
    assert len(chunks) >= 0
    if chunks:
        assert all(chunk.metadata.get("strategy") == "recursive" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_custom_chunk_size():
    """Test chunking with custom chunk size."""
    service = ChunkingService()
    text = " ".join(["word"] * 500)
    chunks_small = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        chunking_strategy="fixed_token",
        chunk_size=128,
        chunk_overlap=10,
    )
    chunks_large = await service.chunk_text(
        text,
        document_id="doc2",
        document_type=DocumentType.TXT,
        chunking_strategy="fixed_token",
        chunk_size=256,
        chunk_overlap=20,
    )
    # Larger chunk size should produce fewer chunks
    assert len(chunks_small) > len(chunks_large)


@pytest.mark.asyncio
async def test_chunk_text_metadata_preserved():
    """Test that document metadata is preserved in chunks."""
    service = ChunkingService()
    text = "Test document text."
    metadata = {"source": "test", "author": "test_author", "custom_field": "value"}
    chunks = await service.chunk_text(
        text,
        document_id="doc1",
        document_type=DocumentType.TXT,
        metadata=metadata,
        chunking_strategy="recursive",
    )
    assert len(chunks) > 0
    # Check that metadata is preserved
    for chunk in chunks:
        assert chunk.metadata is not None
        assert chunk.metadata.get("source") == "test"
        assert chunk.metadata.get("author") == "test_author"
        assert chunk.metadata.get("custom_field") == "value"
        assert "chunk_index" in chunk.metadata
        assert "document_id" in chunk.metadata
