"""
Chunking Service for Stateless Core v1

This module implements the core chunking strategies for document processing
in the corpus management enhancement.

Supports 7 chunking strategies:
- 3 core strategies (always available)
- 2 expert strategies (feature-flagged)
- 2 legacy strategies (maintain compatibility)
"""

import re
import time
from typing import Any

from ..schemas.chunking_enums import (
    ChunkingAnalysis,
    ChunkingConfig,
    ChunkingResult,
    ChunkingStrategy,
)


class ChunkingService:
    """Service for document chunking using various strategies."""

    def __init__(self) -> None:
        """Initialize the chunking service."""
        self._tokenizer_cache: dict[str, Any] = {}

    async def chunk_document(
        self,
        text: str,
        config: ChunkingConfig,
        document_id: str | None = None,
    ) -> ChunkingResult:
        """
        Chunk a document using the specified strategy.

        Args:
            text: The text content to chunk
            config: Chunking configuration
            document_id: Optional document identifier for logging

        Returns:
            ChunkingResult with chunks and metadata
        """
        start_time = time.time()

        # Route to appropriate chunking strategy
        if config.strategy == ChunkingStrategy.FIXED_TOKEN:
            chunks = await self._chunk_fixed_token(text, config)
        elif config.strategy == ChunkingStrategy.SLIDING_TOKEN:
            chunks = await self._chunk_sliding_token(text, config)
        elif config.strategy == ChunkingStrategy.HEADING_AWARE:
            chunks = await self._chunk_heading_aware(text, config)
        elif config.strategy == ChunkingStrategy.SENTENCE_PARAGRAPH:
            chunks = await self._chunk_sentence_paragraph(text, config)
        elif config.strategy == ChunkingStrategy.TABLE_AWARE:
            chunks = await self._chunk_table_aware(text, config)
        elif config.strategy == ChunkingStrategy.SEMANTIC_ADAPTIVE:
            chunks = await self._chunk_semantic_adaptive(text, config)
        elif config.strategy == ChunkingStrategy.PAGE_BLOCK:
            chunks = await self._chunk_page_block(text, config)
        elif config.strategy == ChunkingStrategy.RECURSIVE:
            chunks = await self._chunk_recursive(text, config)
        else:
            raise ValueError(f"Unsupported chunking strategy: {config.strategy}")

        processing_time = int((time.time() - start_time) * 1000)

        # Calculate metrics
        total_tokens = sum(len(chunk.split()) for chunk in chunks)
        avg_chunk_size = total_tokens / len(chunks) if chunks else 0

        return ChunkingResult(
            strategy=config.strategy,
            chunks=chunks,
            chunk_count=len(chunks),
            total_tokens=total_tokens,
            avg_chunk_size=avg_chunk_size,
            processing_time_ms=processing_time,
            metadata={
                "document_id": document_id or "unknown",
                "strategy": config.strategy.value,
                "chunk_size": str(config.chunk_size),
            },
        )

    async def _chunk_fixed_token(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text using fixed token size strategy."""
        words = text.split()
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_tokens = 0

        for word in words:
            if current_tokens + 1 > config.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(word)
            current_tokens += 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def _chunk_sliding_token(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text using sliding window strategy with overlap."""
        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = min(start + config.chunk_size, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))

            # Move start position with overlap
            start += config.chunk_size - config.chunk_overlap

        return chunks

    async def _chunk_heading_aware(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text respecting heading boundaries."""
        # Split by headings (lines starting with #)
        sections = re.split(r"\n(?=#+\s)", text)
        chunks = []
        current_chunk = ""

        for section in sections:
            if not section.strip():
                continue

            # If adding this section would exceed chunk size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk.split()) + len(section.split()) > config.chunk_size
            ):
                chunks.append(current_chunk.strip())
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def _chunk_sentence_paragraph(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text respecting sentence and paragraph boundaries."""
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # If adding this paragraph would exceed chunk size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk.split()) + len(paragraph.split()) > config.chunk_size
            ):
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def _chunk_table_aware(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text respecting table boundaries."""
        # Simple table detection by looking for pipe characters
        lines = text.split("\n")
        chunks = []
        current_chunk = ""
        in_table = False

        for line in lines:
            is_table_line = "|" in line and line.strip()

            if is_table_line and not in_table:
                # Starting a new table, finalize current chunk if needed
                if current_chunk and len(current_chunk.split()) > config.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                in_table = True
            elif not is_table_line and in_table:
                # Ending a table, finalize current chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                in_table = False

            # Add line to current chunk
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

            # Check if we need to split due to size
            if len(current_chunk.split()) > config.chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = ""

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def _chunk_semantic_adaptive(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text using semantic similarity (simplified implementation)."""
        # For now, fall back to sentence-paragraph chunking
        # In a full implementation, this would use embeddings to find semantic boundaries
        return await self._chunk_sentence_paragraph(text, config)

    async def _chunk_page_block(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text by page blocks (simplified implementation)."""
        # Split by page breaks (form feed characters or explicit page markers)
        pages = re.split(r"\f|\n---\n", text)
        chunks = []

        for page in pages:
            if not page.strip():
                continue

            # If page is too large, split it further
            if len(page.split()) > config.chunk_size:
                # Split large pages by paragraphs
                sub_chunks = await self._chunk_sentence_paragraph(page, config)
                chunks.extend(sub_chunks)
            else:
                chunks.append(page.strip())

        return chunks

    async def _chunk_recursive(self, text: str, config: ChunkingConfig) -> list[str]:
        """Chunk text using recursive splitting (legacy compatibility)."""
        # Simple recursive splitting by sentences, then words
        sentences = re.split(r"[.!?]+", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if not sentence.strip():
                continue

            if (
                current_chunk
                and len(current_chunk.split()) + len(sentence.split()) > config.chunk_size
            ):
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += ". " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def analyze_chunking_quality(
        self,
        result: ChunkingResult,
        document_id: str,
    ) -> ChunkingAnalysis:
        """
        Analyze the quality of a chunking result.

        Args:
            result: The chunking result to analyze
            document_id: Document identifier

        Returns:
            ChunkingAnalysis with quality metrics
        """
        from uuid import UUID

        chunks = result.chunks
        if not chunks:
            return ChunkingAnalysis(
                strategy=result.strategy,
                document_id=UUID(document_id),
                chunk_count=0,
                avg_chunk_size=0.0,
                size_variance=0.0,
                overlap_ratio=0.0,
                quality_score=0.0,
                recommendations=["No chunks generated"],
            )

        # Calculate size variance
        chunk_sizes = [len(chunk.split()) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        variance = sum((size - avg_size) ** 2 for size in chunk_sizes) / len(chunk_sizes)

        # Calculate overlap ratio (simplified)
        overlap_ratio = 0.0  # Would need more complex analysis for real overlap

        # Calculate quality score (simplified)
        size_consistency = 1.0 - (variance / (avg_size**2)) if avg_size > 0 else 0.0
        coverage_score = min(1.0, len(chunks) / 10)  # Prefer reasonable number of chunks
        quality_score = (size_consistency + coverage_score) / 2

        # Generate recommendations
        recommendations = []
        if variance > avg_size * 0.5:
            recommendations.append("Consider adjusting chunk size for more consistent chunks")
        if len(chunks) < 3:
            recommendations.append("Document may be too short for effective chunking")
        if len(chunks) > 100:
            recommendations.append("Consider larger chunk size to reduce fragmentation")

        return ChunkingAnalysis(
            strategy=result.strategy,
            document_id=UUID(document_id),
            chunk_count=len(chunks),
            avg_chunk_size=avg_size,
            size_variance=variance,
            overlap_ratio=overlap_ratio,
            quality_score=quality_score,
            recommendations=recommendations,
        )
