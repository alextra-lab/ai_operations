"""
Markdown format extractor.
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="markdown_extration")


async def extract_from_markdown(
    content: bytes, config: ContentExtractorConfig, _importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from Markdown document.

    Args:
        content: Markdown document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    metadata = {
        "extraction_method": "markdown",
    }

    try:
        # Decode bytes to string
        try:
            markdown_text = content.decode("utf-8")
        except UnicodeDecodeError:
            markdown_text = content.decode("latin-1")  # Fallback encoding

        # Extract headings for metadata
        headings = []
        current_level = 0
        for line in markdown_text.splitlines():
            if line.startswith("#"):
                # Count the number of # symbols to determine heading level
                level = 0
                for char in line:
                    if char == "#":
                        level += 1
                    else:
                        break

                if level > 0 and level <= 6:  # Valid heading levels are 1-6
                    heading_text = line[level:].strip()
                    if heading_text:  # Ensure there's actual content
                        headings.append({"level": level, "text": heading_text})
                        # Track top-level heading
                        if level == 1 and current_level == 0:
                            current_level = level
                            metadata["title"] = heading_text  # type: ignore[assignment]

        if headings:
            metadata["headings_count"] = len(headings)  # type: ignore[assignment]
            metadata["headings"] = headings[:10]  # type: ignore[assignment] # Limit to first 10 headings

        # Count code blocks
        code_blocks = 0
        in_code_block = False
        for line in markdown_text.splitlines():
            line = line.strip()
            if line.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:  # Start of a code block
                    code_blocks += 1

        if code_blocks > 0:
            metadata["code_blocks"] = code_blocks  # type: ignore[assignment]

        # Basic statistics
        metadata["lines"] = len(markdown_text.splitlines())  # type: ignore[assignment]
        metadata["character_count"] = len(markdown_text)  # type: ignore[assignment]

        # Detect language if configured
        if config.language_detection and markdown_text:
            from ..text_extractor_utils import detect_language

            metadata["language"] = await detect_language(markdown_text)  # type: ignore[assignment]

        # Apply length limit if configured
        if config.max_content_length and len(markdown_text) > config.max_content_length:
            full_text = markdown_text[: config.max_content_length]
            metadata["truncated"] = True  # type: ignore[assignment]
        else:
            full_text = markdown_text

        return full_text, metadata

    except Exception as e:
        logger.error(f"Markdown extraction failed: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to extract text from Markdown: {e!s}")
