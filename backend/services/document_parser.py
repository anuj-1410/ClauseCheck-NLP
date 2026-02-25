"""
ClauseCheck – Document Parser Service
Extracts text from PDF, DOCX, and TXT files.
Detects whether a PDF is scanned (image-based) and needs OCR.
"""

import io
import logging
from pathlib import Path
from typing import Tuple

from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


def parse_document(file_bytes: bytes, filename: str) -> Tuple[str, bool]:
    """
    Parse a document and extract its text content.

    Returns:
        Tuple of (extracted_text, needs_ocr)
        - If needs_ocr is True, the text is empty/minimal and OCR is required.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return _parse_txt(file_bytes), False
    elif ext == ".docx":
        return _parse_docx(file_bytes), False
    elif ext == ".pdf":
        return _parse_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_txt(file_bytes: bytes) -> str:
    """Parse plain text file."""
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, Exception):
            continue
    return file_bytes.decode("utf-8", errors="replace")


def _parse_docx(file_bytes: bytes) -> str:
    """Parse DOCX file using python-docx."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _parse_pdf(file_bytes: bytes) -> Tuple[str, bool]:
    """
    Parse PDF file. If text extraction yields very little text,
    flag it as needing OCR.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts).strip()

        # If we got very little text, it's likely a scanned PDF
        if len(full_text) < 50:
            logger.info("PDF appears to be scanned (minimal text extracted). OCR needed.")
            return "", True

        return full_text, False

    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}. Will attempt OCR.")
        return "", True
