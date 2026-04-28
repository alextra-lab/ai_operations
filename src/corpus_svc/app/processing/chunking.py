"""
Document chunking utilities for the Retriever service.

This module provides utilities for chunking document text into smaller pieces
for more effective storage, retrieval, and embedding.

P4-DOC-07: Updated to support all chunking strategies via ChunkingService.
"""

import re
from typing import Any

from shared.logging_utils.fastapi import configure_logging
from shared.telemetry_utils.telemetry import create_span

from ..schemas.chunk import (
    ChunkCreate,
    ChunkingPipelineConfig,
    RecursiveChunkingConfig,
)
from ..schemas.chunking_enums import ChunkingConfig, ChunkingStrategy
from ..schemas.document import DocumentType
from ..services.chunking_service import ChunkingService as CoreChunkingService

# Configure logger using shared logging utilities
logger = configure_logging(service_name="chunking_processing")


class ChunkingService:
    """Service for chunking document text into smaller chunks."""

    def __init__(self, config: ChunkingPipelineConfig | None = None):
        """
        Initialize the chunking service with configuration.

        Args:
            config: Chunking pipeline configuration (kept for backward compatibility)
        """
        self.config = config or ChunkingPipelineConfig()  # type: ignore[call-arg]
        self.core_service = CoreChunkingService()
        logger.info("Chunking service initialized with full strategy support")

    async def chunk_text(
        self,
        text: str,
        document_id: str,
        document_type: DocumentType,
        metadata: dict[str, Any] | None = None,
        chunking_strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> list[ChunkCreate]:
        """
        Chunk document text into smaller pieces.

        Args:
            text: Document text to chunk
            document_id: ID of the parent document
            document_type: Type of document
            metadata: Document metadata to include in chunks
            chunking_strategy: Strategy to use (fixed_token, sliding_token, heading_aware, etc.)
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens

        Returns:
            List of created chunk models
        """
        with create_span("chunk_text") as span:
            span.set_attribute("document.id", document_id)
            span.set_attribute("document.type", document_type)
            span.set_attribute("chunking.strategy", chunking_strategy)
            span.set_attribute("chunking.chunk_size", chunk_size)
            span.set_attribute("chunking.chunk_overlap", chunk_overlap)

            try:
                # Convert string strategy to enum
                strategy_enum = ChunkingStrategy(chunking_strategy)
            except ValueError:
                logger.warning(
                    f"Invalid chunking strategy '{chunking_strategy}', falling back to recursive"
                )
                strategy_enum = ChunkingStrategy.RECURSIVE

            # Create chunking config
            chunking_config = ChunkingConfig(
                strategy=strategy_enum,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_size=64,
                max_chunk_size=2048,
                preserve_whitespace=True,
                respect_sentence_boundaries=True,
            )

            # Use core chunking service to chunk the document
            result = await self.core_service.chunk_document(
                text=text,
                config=chunking_config,
                document_id=document_id,
            )

            # Convert ChunkingResult chunks (list[str]) to ChunkCreate models
            chunks: list[ChunkCreate] = []
            for idx, chunk_text in enumerate(result.chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata["chunk_index"] = idx
                chunk_metadata["document_id"] = document_id
                chunk_metadata["content_length"] = len(chunk_text)
                # Use the resolved strategy (after fallback) not the original request
                chunk_metadata["strategy"] = strategy_enum.value

                chunk = ChunkCreate(
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk_text,
                    metadata=chunk_metadata,
                    parent_chunk_id=None,
                    depth=0,
                    embedding=None,
                    embedding_model=None,
                    embedding_provider=None,
                    embedding_dimensions=None,
                    embedding_id=None,
                )
                chunks.append(chunk)

            logger.info(
                f"Chunked document {document_id}: {len(chunks)} chunks created",
                extra={
                    "document_id": document_id,
                    "chunks_count": len(chunks),
                },
            )

            # Add span attributes
            span.set_attribute("chunking.chunks_count", len(chunks))
            # Calculate average chunk size from metadata
            if chunks:
                chunk_sizes = []
                for chunk in chunks:
                    if chunk.metadata and "content_length" in chunk.metadata:
                        chunk_sizes.append(chunk.metadata["content_length"])
                avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
                span.set_attribute("chunking.avg_chunk_size", avg_size)

            return chunks


class RecursiveChunker:
    """Recursive text chunking strategy."""

    def __init__(
        self,
        config: RecursiveChunkingConfig,
        document_type: DocumentType,
    ):
        """
        Initialize recursive chunker with configuration.

        Args:
            config: Chunking configuration
            document_type: Type of document being chunked
        """
        self.config = config
        self.document_type = document_type

        # Adjust chunking parameters based on document type if enabled
        if self.config.adapt_to_content_type:
            self._adapt_to_document_type()

    def _adapt_to_document_type(self) -> None:
        """Adjust chunking parameters based on document type."""
        if self.document_type == DocumentType.PDF:
            # PDFs often have well-defined page boundaries
            self.config.separators = ["\n\n", "\n", ". ", " "]
            self.config.max_chunk_size = 256
        elif self.document_type == DocumentType.MARKDOWN:
            # Markdown has headers that make natural chunk boundaries
            self.config.separators = [
                "\n## ",
                "\n### ",
                "\n#### ",
                "\n\n",
                "\n",
                ". ",
                " ",
            ]
            self.config.max_chunk_size = 256
        elif self.document_type == DocumentType.HTML:
            # HTML has tags that make natural chunk boundaries
            self.config.separators = [
                "\n<h2",
                "\n<h3",
                "\n<div",
                "\n<p",
                "\n\n",
                "\n",
                ". ",
                " ",
            ]
            self.config.max_chunk_size = 256
        elif self.document_type == DocumentType.TXT:
            # Plain text should be chunked by paragraphs and sentences
            # Plain text should be chunked by paragraphs and sentences
            self.config.separators = ["\n\n", "\n", ". ", ", ", " "]
            self.config.max_chunk_size = 256

    async def chunk(
        self,
        text: str,
        document_id: str,
        metadata: dict[str, Any],
    ) -> list[ChunkCreate]:
        """
        Recursively chunk text into smaller pieces.

        Args:
            text: Text to chunk
            document_id: ID of the parent document
            metadata: Metadata to include in chunks

        Returns:
            List of chunk models
        """
        with create_span("recursive_chunk") as span:
            # Initialize chunks list
            chunks: list[ChunkCreate] = []

            # Validate input
            if not text or not text.strip():
                logger.warning(f"Empty text provided for document {document_id}")
                return chunks

            # Clean up text
            text = self._clean_text(text)

            # Check if text is small enough to be a single chunk
            if len(text) <= self.config.max_chunk_size:
                chunk = self._create_chunk(text, document_id, 0, metadata)
                chunks.append(chunk)
                return chunks

            # Split text into chunks
            chunk_index = 0

            # Try each separator in order
            for separator in self.config.separators:
                # Split text by separator
                splits = self._split_by_separator(text, separator)

                # If splitting produced valid chunks, process them
                if self._is_valid_split(splits):
                    current_chunk_text: list[str] = []
                    current_chunk_size = 0

                    for split in splits:
                        # If adding this split would exceed max size, create a chunk
                        if (
                            current_chunk_size + len(split) + len(separator)
                            > self.config.max_chunk_size
                        ) and current_chunk_text:
                            # Only create chunk if there's content
                            chunk_text = separator.join(current_chunk_text)
                            chunk = self._create_chunk(
                                chunk_text, document_id, chunk_index, metadata
                            )
                            chunks.append(chunk)
                            chunk_index += 1

                            # Start a new chunk with overlap
                            if self.config.overlap_size > 0 and current_chunk_text:
                                # Take the last part of previous chunk for overlap
                                overlap_text = current_chunk_text[-1]
                                if len(overlap_text) > self.config.overlap_size:
                                    # Truncate to overlap size from the end
                                    overlap_text = overlap_text[-self.config.overlap_size :]
                                current_chunk_text = [overlap_text]
                                current_chunk_size = len(overlap_text)
                            else:
                                current_chunk_text = []
                                current_chunk_size = 0

                        # Add split to current chunk
                        current_chunk_text.append(split)
                        current_chunk_size += len(split) + len(separator)

                    # Create final chunk if there's leftover content
                    if current_chunk_text:
                        chunk_text = separator.join(current_chunk_text)
                        chunk = self._create_chunk(chunk_text, document_id, chunk_index, metadata)
                        chunks.append(chunk)

                    # If we have chunks, we're done with this level of splitting
                    if chunks:
                        span.set_attribute("chunking.separator_used", separator)
                        span.set_attribute("chunking.splits_count", len(splits))
                        break

            # If no valid splits were found, resort to character-level chunking
            if not chunks:
                logger.warning(
                    f"No valid splits found for document {document_id}, "
                    f"using character-level chunking"
                )

                # Split text by character chunks
                for i in range(0, len(text), self.config.max_chunk_size - self.config.overlap_size):
                    chunk_text = text[i : i + self.config.max_chunk_size]
                    chunk = self._create_chunk(chunk_text, document_id, chunk_index, metadata)
                    chunks.append(chunk)
                    chunk_index += 1

            logger.info(
                f"Created {len(chunks)} chunks for document {document_id} using recursive chunking"
            )

            return chunks

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for chunking.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Trim leading/trailing whitespace
        return text.strip()

    def _split_by_separator(self, text: str, separator: str) -> list[str]:
        """
        Split text by separator.

        Args:
            text: Text to split
            separator: Separator to split by

        Returns:
            List of text splits
        """
        # Handle special case for newlines and spaces
        if separator in ["\n", "\n\n", " "]:
            # Use regular expression for consecutive newlines
            splits = re.split("\\n\\s*\\n", text) if separator == "\n\n" else text.split(separator)

            # Filter out empty splits
            return [s for s in splits if s.strip()]

        # For other separators, use normal split
        return text.split(separator)

    def _is_valid_split(self, splits: list[str]) -> bool:
        """
        Check if a list of splits is valid for chunking.

        Args:
            splits: List of text splits

        Returns:
            True if splits are valid, False otherwise
        """
        # Need at least 2 splits to be worthwhile
        if len(splits) < 2:
            return False

        # Check if any splits are too large
        return all(len(split) <= self.config.max_chunk_size for split in splits)

    def _create_chunk(
        self,
        text: str,
        document_id: str,
        chunk_index: int,
        document_metadata: dict[str, Any],
    ) -> ChunkCreate:
        """
        Create a chunk model.

        Args:
            text: Chunk text content
            document_id: ID of the parent document
            chunk_index: Index of the chunk within the document
            document_metadata: Document metadata

        Returns:
            ChunkCreate model
        """
        # Filter document metadata
        chunk_metadata = {}

        # Include only specified metadata fields
        if self.config.metadata_fields:
            for field in self.config.metadata_fields:
                if field in document_metadata:
                    chunk_metadata[field] = document_metadata[field]
        else:
            # Include all metadata if no fields specified
            chunk_metadata = document_metadata.copy()

        # Add chunk-specific metadata
        chunk_metadata["chunk_index"] = chunk_index
        chunk_metadata["document_id"] = document_id
        chunk_metadata["content_length"] = len(text)
        # Create chunk model with all required and optional fields
        chunk = ChunkCreate(
            document_id=document_id,
            chunk_index=chunk_index,
            content=text,  # Pass content directly
            metadata=chunk_metadata,
            parent_chunk_id=None,
            depth=0,
            embedding=None,
            embedding_model=None,
            embedding_provider=None,
            embedding_dimensions=None,
            embedding_id=None,
        )
        # Remove content from metadata as it's now a direct field
        if "content" in chunk_metadata:
            del chunk_metadata["content"]

        return chunk
