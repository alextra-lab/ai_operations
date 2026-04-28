"""
Text file format extractor.
"""

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig
from ..text_extractor_utils import detect_language

logger = configure_logging(service_name="text_extraction")


async def extract_from_text(content: str, config: ContentExtractorConfig) -> tuple[str, dict]:
    """
    Extract text from plaintext document.

    Args:
        content: Text document content as string
        config: Content extraction configuration

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    metadata = {
        "extraction_method": "plaintext",
        "line_count": content.count("\n") + 1,
    }

    # Detect language if configured
    if config.language_detection and content:
        metadata["language"] = await detect_language(content)

    # Apply length limit if configured
    if config.max_content_length and len(content) > config.max_content_length:
        content = content[: config.max_content_length]
        metadata["truncated"] = True

    return content, metadata
