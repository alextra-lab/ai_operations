"""
PDF format extractor.
"""

from io import BytesIO
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ....schemas.chunk import ContentExtractorConfig

logger = configure_logging(service_name="pfd_extraction")


async def extract_from_pdf(
    content: bytes, config: ContentExtractorConfig, importers: dict[str, Any]
) -> tuple[str, dict]:
    """
    Extract text from PDF document.

    Args:
        content: PDF document content as bytes
        config: Content extraction configuration
        importers: Dictionary of lazily imported modules

    Returns:
        Tuple of extracted text and metadata dictionary
    """
    # Lazily import pdfplumber
    if "pdfplumber" not in importers:
        try:
            import pdfplumber

            importers["pdfplumber"] = pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed, cannot extract text from PDF")
            from ..error import ExtractionError

            raise ExtractionError(
                "pdfplumber not installed, cannot extract text from PDF. "
                "Install with: pip install pdfplumber"
            )

    pdfplumber = importers["pdfplumber"]

    metadata: dict[str, Any] = {
        "extraction_method": "pdfplumber",
        "pages": 0,
        "has_images": False,
    }

    extracted_text: list[str] = []

    with BytesIO(content) as pdf_stream:
        # Debug: Try to open PDF and log result
        try:
            with pdfplumber.open(pdf_stream) as pdf:
                metadata["pages"] = len(pdf.pages)  # type: ignore[assignment]
                logger.info(f"[DEBUG] Opened PDF in extract_from_pdf, pages: {len(pdf.pages)}")

                # Extract text from each page
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""

                    # Add page number as header
                    if page_text:
                        extracted_text.append(f"\n\n--- Page {i + 1} ---\n\n")
                        extracted_text.append(page_text)

                    # Check for images if configured
                    if config.extract_images and page.images:
                        metadata["has_images"] = True  # type: ignore[assignment]

                        # Perform OCR if configured
                        if config.ocr_images:
                            # Import pytesseract lazily
                            if "pytesseract" not in importers:
                                try:
                                    import pytesseract
                                    from PIL import Image

                                    importers["pytesseract"] = pytesseract
                                    importers["PIL"] = Image
                                except ImportError:
                                    logger.warning("pytesseract not installed, cannot perform OCR")
                                    continue

                            pytesseract = importers["pytesseract"]
                            image_cls = importers["PIL"]

                            # OCR each image
                            for img in page.images:
                                try:
                                    # Extract image
                                    image_obj = page.crop(img["bbox"])
                                    img_bytes = BytesIO()
                                    image_obj.to_image().save(img_bytes, format="PNG")
                                    img_bytes.seek(0)

                                    # Perform OCR
                                    ocr_text = pytesseract.image_to_string(
                                        image_cls.open(img_bytes), lang="eng"
                                    )

                                    if ocr_text.strip():
                                        extracted_text.append("\n\n--- Image Text ---\n\n")
                                        extracted_text.append(ocr_text.strip())
                                except Exception as e:
                                    logger.warning(f"OCR failed: {e!s}")

                    # Extract tables if configured
                    if config.extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            for t_idx, table in enumerate(tables):
                                extracted_text.append(f"\n\n--- Table {t_idx + 1} ---\n\n")
                                for row in table:
                                    # Convert all cell values to strings and join with tabs
                                    row_text = "\t".join([str(cell or "") for cell in row])
                                    extracted_text.append(row_text)
                                    extracted_text.append("\n")

        except Exception as e:
            logger.error("Failed to open PDF in extract_from_pdf: %s", e)
            pdf_stream.seek(0)  # Reset pointer for main extraction attempt
            logger.error(f"PDF extraction failed: {e!s}", exc_info=True)
            from ..error import ExtractionError

            raise ExtractionError(f"Failed to extract text from PDF: {e!s}")

    # Combine all extracted text
    full_text = "".join(extracted_text)

    # Detect language if configured
    if config.language_detection and full_text:
        from ..text_extractor_utils import detect_language

        metadata["language"] = await detect_language(full_text)  # type: ignore[assignment]

    # Apply length limit if configured
    if config.max_content_length and len(full_text) > config.max_content_length:
        full_text = full_text[: config.max_content_length]
        metadata["truncated"] = True  # type: ignore[assignment]

    return full_text, metadata
