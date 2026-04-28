"""
CSV format extractor.
"""

from io import StringIO
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="cvs_extraction")


async def extract_from_csv(
    content: bytes, config: ContentExtractorConfig, importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from CSV document.

    Args:
        content: CSV document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    # Lazily import csv
    if "csv" not in importers:
        try:
            import csv

            importers["csv"] = csv
        except ImportError:
            logger.error("csv module not available")
            from ..error import ExtractionError

            raise ExtractionError("Failed to import csv module")

    csv_module = importers["csv"]

    metadata = {
        "extraction_method": "csv",
        "rows": 0,
        "columns": 0,
    }

    try:
        # Decode bytes to string
        try:
            csv_content = content.decode("utf-8")
        except UnicodeDecodeError:
            csv_content = content.decode("latin-1")  # Fallback encoding

        # Parse CSV
        rows: list[list[str]] = []
        csv_file = StringIO(csv_content)
        reader = csv_module.reader(csv_file)

        # Extract header row
        header = next(reader, None)
        if header:
            rows.append(header)
            metadata["columns"] = len(header)  # type: ignore[assignment]

        # Extract data rows
        row_count = 0
        for row in reader:
            rows.append(row)
            row_count += 1

        metadata["rows"] = row_count

        # Convert to text
        if config.structured_to_text_format == "markdown":
            # Format as markdown table
            extracted_text = []

            if header:
                # Add header
                extracted_text.append("| " + " | ".join(header) + " |")
                # Add separator
                extracted_text.append("| " + " | ".join(["---"] * len(header)) + " |")

            # Add rows
            for row in rows[1:] if header else rows:
                # Ensure row has same number of columns as header
                if header and len(row) < len(header):
                    row.extend([""] * (len(header) - len(row)))
                extracted_text.append("| " + " | ".join(row) + " |")

            full_text = "\n".join(extracted_text)

        else:
            # Default format: tab-separated
            extracted_text = []
            for row in rows:
                extracted_text.append("\t".join(row))
            full_text = "\n".join(extracted_text)

        # Detect language if configured
        if config.language_detection and full_text:
            from ..text_extractor_utils import detect_language

            metadata["language"] = await detect_language(full_text)  # type: ignore[assignment]

        # Apply length limit if configured
        if config.max_content_length and len(full_text) > config.max_content_length:
            full_text = full_text[: config.max_content_length]
            metadata["truncated"] = True  # type: ignore[assignment]

        return full_text, metadata

    except Exception as e:
        logger.error(f"CSV extraction failed: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to extract text from CSV: {e!s}")
