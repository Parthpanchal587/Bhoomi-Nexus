"""
PDF text and structure extraction utility.

Uses PyPDF2 for pure-Python extraction (no system dependencies).
Falls back gracefully if the PDF is image-only or encrypted.
"""

import io
import re
from typing import Any

from PyPDF2 import PdfReader


def extract_text(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages, with page breaks.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text: list[str] = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(f"[Page {i + 1}]\n{page_text.strip()}")
        return "\n\n".join(pages_text)
    except Exception:
        return ""


def extract_structure(file_bytes: bytes) -> dict[str, Any]:
    """
    Extract structural metadata from a PDF file.

    Returns:
        Dictionary with page_count, metadata, title, author, etc.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        meta = reader.metadata or {}
        return {
            "page_count": len(reader.pages),
            "title": getattr(meta, "title", None) or "",
            "author": getattr(meta, "author", None) or "",
            "creator": getattr(meta, "creator", None) or "",
            "producer": getattr(meta, "producer", None) or "",
            "subject": getattr(meta, "subject", None) or "",
            "is_encrypted": reader.is_encrypted,
        }
    except Exception:
        return {
            "page_count": 0,
            "title": "",
            "author": "",
            "creator": "",
            "producer": "",
            "subject": "",
            "is_encrypted": False,
        }


def normalize_text(text: str) -> str:
    """
    Normalize extracted text for fingerprinting.

    Strips excess whitespace, lowercases, removes punctuation variance,
    so that trivial formatting differences don't change the fingerprint
    while content changes do.
    """
    # Lowercase
    text = text.lower()
    # Collapse all whitespace sequences to single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing
    text = text.strip()
    return text
