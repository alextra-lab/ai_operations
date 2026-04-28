"""
Utility functions for text extraction.
"""

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="text_extractor_utils")


async def detect_language(text: str) -> str:
    """
    Detect language of text.

    Args:
        text: Text to detect language for

    Returns:
        Detected language code
    """
    # Import langdetect lazily
    try:
        from langdetect import detect as langdetect_detect

        try:
            # Use only first 10000 characters for language detection
            sample_text = text[:10000]
            if not sample_text:
                return "unknown"

            return str(langdetect_detect(sample_text))
        except Exception as e:
            logger.warning(f"Language detection failed: {e!s}")
            return "unknown"
    except ImportError:
        logger.warning("langdetect not installed, cannot detect language")
        return "unknown"
