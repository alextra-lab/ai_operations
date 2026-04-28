#!/usr/bin/env python3
"""
Extract metadata from PDF files for demo script enhancement.
"""

import io
import json
from pathlib import Path
from typing import Any


def extract_pdf_metadata(pdf_path: str) -> dict[str, Any]:
    """Extract metadata from a PDF file using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        print("pdfplumber not installed. Install with: pip install pdfplumber")
        return {}

    metadata = {
        "file_name": Path(pdf_path).name,
        "file_size": Path(pdf_path).stat().st_size,
        "extraction_method": "pdfplumber",
        "pages": 0,
        "has_images": False,
        "file_type": "pdf",
        "file_extension": "pdf",
    }

    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            metadata["pages"] = len(pdf.pages)
            metadata["page_count"] = len(pdf.pages)

            # Extract PDF metadata
            if hasattr(pdf, "metadata") and pdf.metadata:
                pdf_meta = pdf.metadata
                if pdf_meta.get("Title"):
                    metadata["title"] = pdf_meta["Title"]
                if pdf_meta.get("Author"):
                    metadata["author"] = pdf_meta["Author"]
                if pdf_meta.get("Subject"):
                    metadata["subject"] = pdf_meta["Subject"]
                if pdf_meta.get("Creator"):
                    metadata["creator"] = pdf_meta["Creator"]
                if pdf_meta.get("Producer"):
                    metadata["producer"] = pdf_meta["Producer"]
                if pdf_meta.get("CreationDate"):
                    metadata["creation_date"] = str(pdf_meta["CreationDate"])

            # Extract some text content for preview
            text_content = ""
            for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
                page_text = page.extract_text()
                if page_text:
                    text_content += f"--- Page {i+1} --- {page_text[:1000]}\n"

                # Check for images
                if hasattr(page, "images") and page.images:
                    metadata["has_images"] = True

            metadata["content_preview"] = text_content[:2000]  # First 2000 chars
            metadata["language"] = "en"  # Assume English for these docs

    except Exception as e:
        print(f"Error extracting metadata from {pdf_path}: {e}")
        metadata["error"] = str(e)

    return metadata


def main():
    """Extract metadata from all PDFs and print results."""
    # PDFs are in the parent directory relative to scripts/
    pdf_files = ["../nist.cswp.29.pdf", "../nist.sp.800-63-3.pdf", "../uae-ia-regulation-v11-1.pdf"]

    all_metadata = {}

    for pdf_file in pdf_files:
        if Path(pdf_file).exists():
            print(f"\n{'='*60}")
            print(f"EXTRACTING METADATA FROM: {pdf_file}")
            print(f"{'='*60}")

            metadata = extract_pdf_metadata(pdf_file)
            all_metadata[pdf_file] = metadata

            # Print key metadata
            print(f"File: {metadata.get('file_name', 'N/A')}")
            print(f"Size: {metadata.get('file_size', 0):,} bytes")
            print(f"Pages: {metadata.get('pages', 0)}")
            print(f"Title: {metadata.get('title', 'N/A')}")
            print(f"Author: {metadata.get('author', 'N/A')}")
            print(f"Subject: {metadata.get('subject', 'N/A')}")
            print(f"Creator: {metadata.get('creator', 'N/A')}")
            print(f"Producer: {metadata.get('producer', 'N/A')}")
            print(f"Creation Date: {metadata.get('creation_date', 'N/A')}")
            print(f"Has Images: {metadata.get('has_images', False)}")

            # Print content preview
            preview = metadata.get("content_preview", "")
            if preview:
                print("\nContent Preview (first 500 chars):")
                print("-" * 40)
                print(preview[:500] + "..." if len(preview) > 500 else preview)
        else:
            print(f"File not found: {pdf_file}")

    # Save metadata to JSON file for reference
    with open("pdf_metadata.json", "w") as f:
        json.dump(all_metadata, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print("Metadata saved to pdf_metadata.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
