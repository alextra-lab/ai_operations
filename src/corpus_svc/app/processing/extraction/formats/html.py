"""
HTML format extractor.
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="html_extraction")


async def extract_from_html(
    content: bytes, config: ContentExtractorConfig, importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from HTML document.

    Args:
        content: HTML document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    # Lazily import BeautifulSoup
    if "bs4" not in importers:
        try:
            from bs4 import BeautifulSoup

            importers["bs4"] = BeautifulSoup
        except ImportError:
            logger.error("BeautifulSoup not installed, cannot extract text from HTML")
            from ..error import ExtractionError

            raise ExtractionError(
                "BeautifulSoup not installed, cannot extract text from HTML. "
                "Install with: pip install beautifulsoup4"
            )

    beautiful_soup = importers["bs4"]

    metadata = {
        "extraction_method": "beautifulsoup4",
    }

    try:
        # Decode bytes to string
        try:
            html_content = content.decode("utf-8")
        except UnicodeDecodeError:
            html_content = content.decode("latin-1")  # Fallback encoding

        # Parse HTML with BeautifulSoup
        soup = beautiful_soup(html_content, "html.parser")

        # Extract metadata from meta tags
        meta_tags = soup.find_all("meta")
        meta_data = {}
        for tag in meta_tags:
            # Pylance struggles with dynamic attributes/methods on bs4 elements
            if tag.get("name") and tag.get("content"):  # type: ignore[attr-defined]
                meta_data[tag["name"]] = tag["content"]  # type: ignore[index]

        if meta_data:
            metadata["meta_tags"] = meta_data  # type: ignore[assignment]

        # Extract title
        if soup.title and soup.title.string:
            metadata["title"] = soup.title.string.strip()  # type: ignore[assignment]

        # Remove script and style tags
        for script in soup(["script", "style", "iframe", "svg", "noscript"]):  # type: ignore[call-arg]
            script.extract()  # type: ignore[attr-defined]

        # Extract text
        body_text = soup.get_text(separator="\n")

        # Clean up extra whitespace
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # Detect language if configured
        if config.language_detection and clean_text:
            from ..text_extractor_utils import detect_language

            metadata["language"] = await detect_language(clean_text)  # type: ignore[assignment]

        # Apply length limit if configured
        if config.max_content_length and len(clean_text) > config.max_content_length:
            full_text = clean_text[
                : config.max_content_length
            ]  # Use full_text variable name for consistency
            metadata["truncated"] = True  # type: ignore[assignment]
        else:
            full_text = clean_text  # Assign clean_text to full_text if not truncated

        return full_text, metadata  # Ensure returning str, Dict

    except Exception as e:
        logger.error(f"HTML extraction failed: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to extract text from HTML: {e!s}")
