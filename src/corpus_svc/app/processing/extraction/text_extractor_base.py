"""
Base text extractor implementation that delegates to format-specific extractors.
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging
from shared.telemetry_utils.telemetry import create_span

from ...schemas.chunk import ContentExtractorConfig
from ...schemas.document import DocumentType
from .error import ExtractionError
from .formats.csv_format import extract_from_csv
from .formats.docx import extract_from_docx
from .formats.html import extract_from_html
from .formats.json_format import extract_from_json
from .formats.markdown import extract_from_markdown
from .formats.pdf import extract_from_pdf
from .formats.text import extract_from_text
from .formats.xlsx_format import extract_from_xlsx

logger = configure_logging(service_name="text_extractor_base")


class TextExtractor:
    """Extracts text and metadata from documents of various formats."""

    def __init__(self, config: ContentExtractorConfig | None = None):
        """
        Initialize text extractor with configuration.

        Args:
            config: Content extraction configuration
        """
        self.config = config or ContentExtractorConfig()  # type: ignore[call-arg]

        # Import optional dependencies lazily to avoid startup issues
        self._importers: dict[str, Any] = {}

    async def extract_text(
        self, content: str | bytes, document_type: DocumentType, file_name: str
    ) -> tuple[str, dict]:
        """
        Extract text from document content.

        Args:
            content: Document content as string or bytes
            document_type: Type of document
            file_name: Original file name

        Returns:
            Tuple of extracted text and metadata dictionary

        Raises:
            ExtractionError: If extraction fails
        """
        with create_span(f"extract_text_{document_type}") as span:
            span.set_attribute("document.type", document_type)
            span.set_attribute("document.file_name", file_name)

            try:
                # Determine content type and prepare for specific extractors
                if isinstance(content, str):
                    # TXT extractor expects string, others expect bytes
                    if document_type == DocumentType.TXT:
                        text_content = content
                    else:
                        content_bytes = content.encode("utf-8")
                elif isinstance(content, bytes):
                    content_bytes = content
                    # TXT extractor expects string, decode bytes for it
                    if document_type == DocumentType.TXT:
                        try:
                            text_content = content.decode("utf-8")
                        except UnicodeDecodeError:
                            text_content = content.decode("latin-1")  # Fallback encoding
                else:
                    # Handle unexpected types
                    logger.warning(f"Unexpected content type: {type(content)}")
                    raise ExtractionError(f"Unsupported content type: {type(content)}")

                # Choose extractor based on document type
                if document_type == DocumentType.PDF:
                    return await extract_from_pdf(content_bytes, self.config, self._importers)
                if document_type == DocumentType.DOCX:
                    return await extract_from_docx(content_bytes, self.config, self._importers)
                if document_type == DocumentType.TXT:
                    return await extract_from_text(text_content, self.config)
                if document_type == DocumentType.HTML:
                    return await extract_from_html(content_bytes, self.config, self._importers)
                if document_type == DocumentType.MARKDOWN:
                    return await extract_from_markdown(content_bytes, self.config, self._importers)
                if document_type == DocumentType.JSON:
                    return await extract_from_json(content_bytes, self.config, self._importers)
                if document_type == DocumentType.CSV:
                    return await extract_from_csv(content_bytes, self.config, self._importers)
                if document_type == DocumentType.XLSX:
                    return await extract_from_xlsx(content_bytes, self.config, self._importers)
                # Fall back to plaintext for unknown types
                logger.warning(
                    f"No specific extractor for document type {document_type}, falling back to text"
                )
                # Ensure text_content is defined for fallback
                if isinstance(content, bytes):
                    try:
                        text_content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        text_content = content.decode("latin-1")  # Fallback encoding
                else:
                    text_content = content

                return text_content, {"extraction_method": "plaintext"}

            except Exception as e:
                logger.error(f"Text extraction failed: {e!s}", exc_info=True)
                span.record_exception(e)
                raise ExtractionError(f"Failed to extract text: {e!s}")
