"""
Text extraction utilities for the Retriever service.

This module handles text extraction from various document formats,
including PDF, DOCX, HTML, CSV, JSON, and plaintext files.
"""

from shared.logging_utils.fastapi import configure_logging

# Import from the new module structure and re-export
from .extraction.error import ExtractionError
from .extraction.metadata_extractor import MetadataExtractor
from .extraction.text_extractor_base import TextExtractor

# Configure logger using shared logging utilities
logger = configure_logging(service_name="extraction_processing")

# Re-export main classes for backward compatibility
__all__ = ["ExtractionError", "MetadataExtractor", "TextExtractor"]
