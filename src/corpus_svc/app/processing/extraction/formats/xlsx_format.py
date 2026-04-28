"""
XLSX format extractor.
"""

from io import BytesIO
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="xls_extraction")


async def extract_from_xlsx(
    content: bytes, config: ContentExtractorConfig, importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from XLSX document.

    Args:
        content: XLSX document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    # Lazily import openpyxl
    if "openpyxl" not in importers:
        try:
            import openpyxl

            importers["openpyxl"] = openpyxl
        except ImportError:
            logger.error("openpyxl not installed, cannot extract text from Excel files")
            from ..error import ExtractionError

            raise ExtractionError(
                "openpyxl not installed, cannot extract text from Excel files. "
                "Install with: pip install openpyxl"
            )

    openpyxl = importers["openpyxl"]

    metadata = {
        "extraction_method": "openpyxl",
        "sheets": 0,
        "rows": 0,
        "cells": 0,
    }

    try:
        # Load workbook
        with BytesIO(content) as excel_stream:
            workbook = openpyxl.load_workbook(excel_stream, read_only=True, data_only=True)

            # Extract metadata
            sheet_names = workbook.sheetnames
            metadata["sheets"] = len(sheet_names)  # type: ignore[assignment]
            metadata["sheet_names"] = sheet_names  # type: ignore[assignment]

            # Extract document properties
            if workbook.properties:
                props = workbook.properties
                if props.title:
                    metadata["title"] = props.title  # type: ignore[assignment]
                if props.creator:
                    metadata["author"] = props.creator  # type: ignore[assignment]
                if props.created:
                    metadata["created"] = props.created.isoformat()  # type: ignore[assignment]
                if props.modified:
                    metadata["modified"] = props.modified.isoformat()  # type: ignore[assignment]

            # Extract content from sheets
            all_sheets_data: list[str] = []
            total_rows = 0
            total_cells = 0

            for sheet_name in sheet_names:
                sheet = workbook[sheet_name]
                sheet_data: list[str] = []

                # Add sheet header
                sheet_data.append(f"\n\n--- Sheet: {sheet_name} ---\n\n")

                # Process rows
                row_count = 0
                cell_count = 0

                for row in sheet.rows:
                    row_data = []
                    for cell in row:
                        cell_value = cell.value
                        # Convert None to empty string
                        cell_value = "" if cell_value is None else str(cell_value)
                        row_data.append(cell_value)
                        cell_count += 1

                    # Only add non-empty rows (where at least one cell has content)
                    if any(cell.strip() for cell in row_data):
                        # Format based on preference
                        if getattr(config, "structured_to_text_format", "") == "markdown":
                            # Format as markdown table (for first row only)
                            if row_count == 0:
                                sheet_data.append("| " + " | ".join(row_data) + " |")
                                sheet_data.append("| " + " | ".join(["---"] * len(row_data)) + " |")
                            else:
                                sheet_data.append("| " + " | ".join(row_data) + " |")
                        else:
                            # Default: tab-separated
                            sheet_data.append("\t".join(row_data))

                        row_count += 1

                total_rows += row_count
                total_cells += cell_count

                # Add sheet content to overall data
                all_sheets_data.append("\n".join(sheet_data))

            # Update metadata
            metadata["rows"] = total_rows  # type: ignore[assignment]
            metadata["cells"] = total_cells  # type: ignore[assignment]

            # Combine all sheets' content
            full_text = "\n".join(all_sheets_data)

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
        logger.error(f"XLSX extraction failed: {e!s}", exc_info=True)
        from ..error import ExtractionError

        raise ExtractionError(f"Failed to extract text from XLSX: {e!s}")
