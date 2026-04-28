"""
JSON format extractor.
"""

import json
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="json_extration")


async def extract_from_json(
    content: bytes, config: ContentExtractorConfig, _importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from JSON document.

    Args:
        content: JSON document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    metadata = {
        "extraction_method": "json",
        "structure_type": "unknown",
    }

    try:
        # Decode bytes to string
        try:
            json_text = content.decode("utf-8")
        except UnicodeDecodeError:
            json_text = content.decode("latin-1")  # Fallback encoding

        # Parse JSON
        json_data = json.loads(json_text)

        # Determine structure type
        if isinstance(json_data, list):
            metadata["structure_type"] = "array"
            metadata["items_count"] = len(json_data)  # type: ignore[assignment]
        elif isinstance(json_data, dict):
            metadata["structure_type"] = "object"
            metadata["keys_count"] = len(json_data.keys())  # type: ignore[assignment]
            if len(json_data.keys()) > 0:
                metadata["top_level_keys"] = list(json_data.keys())[:10]  # type: ignore[assignment]

        # Format as readable text (with pretty printing)
        formatted_text = json.dumps(json_data, indent=2, ensure_ascii=False)

        # Get metadata about the data
        metadata["character_count"] = len(formatted_text)  # type: ignore[assignment]

        # For arrays of objects, try to extract field names
        if (
            metadata["structure_type"] == "array"
            and len(json_data) > 0
            and isinstance(json_data[0], dict)
        ):
            # Get field names from first item
            field_names = list(json_data[0].keys())
            metadata["field_names"] = field_names  # type: ignore[assignment]
            metadata["first_object_fields_count"] = len(field_names)  # type: ignore[assignment]

        # Detect language if configured
        if config.language_detection and formatted_text:
            from ..text_extractor_utils import detect_language

            metadata["language"] = await detect_language(formatted_text)  # type: ignore[assignment]

        # Apply length limit if configured
        if config.max_content_length and len(formatted_text) > config.max_content_length:
            full_text = formatted_text[: config.max_content_length]
            metadata["truncated"] = True  # type: ignore[assignment]
        else:
            full_text = formatted_text

        return full_text, metadata

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to parse JSON: {e!s}")
    except Exception as e:
        logger.error(f"JSON extraction failed: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to extract text from JSON: {e!s}")
