"""
Document schemas for the Retriever service.

This module defines the Pydantic models for documents and related operations,
including document types, states, and metadata.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.logging_utils.fastapi import configure_logging

# Set up structured logging for this module
logging = configure_logging(service_name="document_schemas")


class DocumentType(str, Enum):
    """Document file types."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    RTF = "rtf"
    XML = "xml"
    PPTX = "pptx"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, extension: str) -> "DocumentType":
        """
        Get document type from file extension.

        Args:
            extension: File extension (with or without leading dot)

        Returns:
            Document type enum value
        """
        # Remove leading dot if present
        if extension.startswith("."):
            extension = extension[1:]

        # Convert to lowercase
        extension = extension.lower()

        # Match extension to document type
        try:
            return cls(extension)
        except ValueError:
            logging.warning(
                f"Unknown file extension '{extension}' encountered in DocumentType.from_extension.",
                extra={"extension": extension},
            )
            return cls.UNKNOWN


class DocumentState(str, Enum):
    """Document processing states."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentClassification(str, Enum):
    """Document classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    UNCLASSIFIED = "unclassified"


class DocumentBase(BaseModel):
    """Base model for document data."""

    title: str = Field(..., description="Document title")
    source: str | None = Field(None, description="Document source (URL, system, etc.)")
    author: str | None = Field(None, description="Document author")
    created_at: datetime | None = Field(None, description="Document creation timestamp")
    file_type: DocumentType = Field(..., description="Document file type")
    tags: list[str] = Field(default_factory=list, description="Document tags")
    classification: DocumentClassification = Field(
        default=DocumentClassification.UNCLASSIFIED,
        description="Document classification",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional document metadata"
    )

    model_config = {
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
    }


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    # content: Union[str, bytes] = Field(..., description="Document content")
    original_file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    file_checksum: str | None = Field(None, description="Document content checksum")

    @field_validator("file_type", mode="before")
    @classmethod
    def validate_file_type(cls, v: Any, info: Any) -> DocumentType:
        """Derive file type from extension if not explicitly provided."""
        values = info.data if hasattr(info, "data") else {}
        if v is None and "file_name" in values:
            file_name = values["file_name"]
            extension = file_name.split(".")[-1] if "." in file_name else "unknown"
            doc_type = DocumentType.from_extension(extension)
            if doc_type == DocumentType.UNKNOWN:
                logging.warning(
                    f"File type could not be determined from file name '{file_name}'.",
                    extra={"file_name": file_name},
                )
            return cast("DocumentType", doc_type)
        return cast("DocumentType", v)

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, v: datetime | None) -> datetime:
        """Use current timestamp if not provided."""
        if v is None:
            now = datetime.now(UTC)
            logging.info(
                "No created_at provided; using current UTC timestamp.",
                extra={"created_at": now.isoformat()},
            )
            return now
        return v


class Document(DocumentBase):
    """Model for a stored document."""

    id: str = Field(..., description="Document unique identifier")
    collection_id: UUID | None = Field(None, description="Collection this document belongs to")
    original_file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    file_checksum: str = Field(..., description="Document content checksum")
    content_compressed: bool = Field(
        default=False, description="Whether content is stored compressed"
    )
    status: DocumentState = Field(
        default=DocumentState.PENDING, description="Document processing state"
    )
    num_chunks: int | None = Field(None, description="Number of chunks created from document")
    error_message: str | None = Field(None, description="Error message if processing failed")

    # Ingestion tracking
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Document ingestion timestamp",
    )
    ingested_by: str | None = Field(None, description="User or process that ingested the document")

    # Legacy fields maintained for backward compatibility
    uploaded_by: str | None = Field(None, description="User ID who uploaded the document")
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Document upload timestamp",
    )
    processed_at: datetime | None = Field(
        None, description="Document processing completion timestamp"
    )

    # Embedding configuration
    embedding_model: str | None = Field(None, description="Embedding model used")
    embedding_provider: str | None = Field(None, description="Embedding provider")
    embedding_dimensions: int | None = Field(None, description="Number of embedding dimensions")
    avg_chunk_size_tokens: int | None = Field(None, description="Average chunk size in tokens")

    # Timestamps
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    """Model for updating document metadata."""

    title: str | None = Field(None, description="Document title")
    source: str | None = Field(None, description="Document source")
    author: str | None = Field(None, description="Document author")
    tags: list[str] | None = Field(None, description="Document tags")
    classification: DocumentClassification | None = Field(
        None, description="Document classification"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional document metadata")
    status: DocumentState | None = Field(None, description="Document processing state")
    # Fields updated by ingestion_service
    num_chunks: int | None = Field(None, description="Number of chunks created from document")
    processed_at: datetime | None = Field(
        None, description="Document processing completion timestamp"
    )
    error_message: str | None = Field(None, description="Error message if processing failed")

    model_config = ConfigDict(use_enum_values=True)


from pydantic import BaseModel, Field


class DocumentResponse(Document):
    """Model for document API response. Excludes content_compressed BYTEA field."""

    # Exclude the content_compressed BYTEA field from API responses for security/size reasons
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc-12345",
                "title": "Example Document",
                "source": "https://example.com/documents/12345",
                "author": "John Doe",
                "created_at": "2023-01-01T12:00:00Z",
                "file_type": "pdf",
                "original_file_name": "example.pdf",
                "file_size": 1024000,
                "file_checksum": "5eb63bbbe01eeed093cb22bb8f5acdc3",
                "content_compressed": True,
                "status": "processed",
                "tags": ["example", "documentation"],
                "classification": "internal",
                "num_chunks": 10,
                "metadata": {
                    "page_count": 42,
                    "language": "en",
                },
                "uploaded_by": "user-12345",
                "uploaded_at": "2023-01-15T08:30:00Z",
                "processed_at": "2023-01-15T08:31:00Z",
                "ingested_at": "2023-01-15T08:30:00Z",
                "ingested_by": "admin_user",
                "embedding_model": "all-minilm-l6-v2",
                "embedding_provider": "sentence-transformers",
                "embedding_dimensions": 384,
                "avg_chunk_size_tokens": 512,
                "updated_at": "2023-01-15T08:31:00Z",
            }
        }
    )


class DocumentSearchQuery(BaseModel):
    """Model for document search query."""

    query: str = Field(..., description="Search query string")
    tags: list[str] | None = Field(None, description="Filter by document tags")
    file_types: list[DocumentType] | None = Field(None, description="Filter by document types")
    classifications: list[DocumentClassification] | None = Field(
        None, description="Filter by document classifications"
    )
    date_from: datetime | None = Field(
        None, description="Filter by document creation date range (start)"
    )
    date_to: datetime | None = Field(
        None, description="Filter by document creation date range (end)"
    )
    metadata_filters: dict[str, Any] | None = Field(
        None, description="Filter by document metadata fields"
    )
    limit: int | None = Field(10, description="Maximum number of results")
    offset: int | None = Field(0, description="Result offset for pagination")

    model_config = {"use_enum_values": True}


class DocumentSearchResult(BaseModel):
    """Model for document search result."""

    document: Document = Field(..., description="Document data")
    score: float = Field(..., description="Search result relevance score")
    highlights: list[str] = Field(
        default_factory=list, description="Highlighted snippets from document content"
    )

    model_config = {"from_attributes": True}


class DocumentSearchResponse(BaseModel):
    """Model for document search API response."""

    results: list[DocumentSearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(..., description="Total number of matching documents")
    query: str = Field(..., description="Search query")
    limit: int = Field(..., description="Maximum number of results")
    offset: int = Field(..., description="Result offset")


class DocumentStatistics(BaseModel):
    """Model for document collection statistics."""

    total_documents: int = Field(..., description="Total number of documents")
    total_size_bytes: int = Field(..., description="Total size of all documents in bytes")
    documents_by_type: dict[str, int] = Field(..., description="Count of documents by file type")
    documents_by_state: dict[str, int] = Field(
        ..., description="Count of documents by processing state"
    )
    documents_by_classification: dict[str, int] = Field(
        ..., description="Count of documents by classification"
    )
    recent_uploads: int = Field(
        ..., description="Number of documents uploaded in the last 24 hours"
    )
    processing_success_rate: float | None = Field(
        None, description="Processing success rate as a percentage"
    )
    avg_chunks_per_document: float | None = Field(
        None, description="Average number of chunks per document"
    )
    avg_processing_time_ms: float | None = Field(
        None, description="Average document processing time in milliseconds"
    )


class DocumentIngestionResponse(BaseModel):
    """Model for document ingestion API response."""

    document_id: str = Field(..., description="Document ID")
    status: str = Field(..., description="Ingestion status")
    message: str = Field(..., description="Status message")


class DocumentDeleteResponse(BaseModel):
    status: str
    document_id: str
