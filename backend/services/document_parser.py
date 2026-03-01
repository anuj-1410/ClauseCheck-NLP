"""
ClauseCheck – Document Parser Service
Extracts text from PDF, DOCX, and TXT files.
Uses pdfplumber for layout-aware PDF parsing that preserves headings & numbering.
Detects whether a PDF is scanned (image-based) and needs OCR.
"""

import io
import re
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Try pdfplumber first, fall back to PyPDF2
try:
    import pdfplumber
    _USE_PDFPLUMBER = True
    logger.info("Using pdfplumber for layout-aware PDF parsing.")
except ImportError:
    from PyPDF2 import PdfReader
    _USE_PDFPLUMBER = False
    logger.info("pdfplumber not found, falling back to PyPDF2.")

from docx import Document


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
    """Parse DOCX file using python-docx, preserving heading structure."""
    doc = Document(io.BytesIO(file_bytes))
    parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # Preserve heading hierarchy with markdown-style markers
        style_name = (para.style.name or "").lower()
        if "heading" in style_name:
            parts.append(f"\n{text}")
        else:
            parts.append(text)
    return "\n".join(parts)


def _parse_pdf(file_bytes: bytes) -> Tuple[str, bool]:
    """
    Parse PDF file with layout awareness.
    If text extraction yields very little text, flag it as needing OCR.
    """
    if _USE_PDFPLUMBER:
        return _parse_pdf_pdfplumber(file_bytes)
    else:
        return _parse_pdf_pypdf2(file_bytes)


def _parse_pdf_pdfplumber(file_bytes: bytes) -> Tuple[str, bool]:
    """
    Layout-aware PDF parsing using pdfplumber.
    Preserves headings (detected via font size) and section numbering.
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
        text_parts = []

        for page in pdf.pages:
            # Extract text preserving layout
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=3,
                layout=False,
            )

            if not page_text:
                continue

            # Preserve section numbering by ensuring newlines before numbered sections
            page_text = re.sub(
                r'(?<!\n)(\d+(?:\.\d+)*\s*[\.\):])',
                r'\n\1',
                page_text
            )

            # Detect and preserve headings via character-level analysis
            try:
                chars = page.chars
                if chars:
                    page_text = _detect_headings_from_chars(chars, page_text)
            except Exception:
                pass  # Char analysis is best-effort

            text_parts.append(page_text)

        pdf.close()
        full_text = "\n".join(text_parts).strip()

        # If we got very little text, it's likely a scanned PDF
        if len(full_text) < 50:
            logger.info("PDF appears to be scanned (minimal text extracted). OCR needed.")
            return "", True

        return full_text, False

    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}. Will attempt OCR.")
        return "", True


def _detect_headings_from_chars(chars: list, page_text: str) -> str:
    """
    Detect headings by finding text with significantly larger font sizes.
    Ensures headings appear on their own lines.
    """
    if not chars:
        return page_text

    # Calculate median font size
    font_sizes = [c.get("size", 12) for c in chars if c.get("text", "").strip()]
    if not font_sizes:
        return page_text

    font_sizes.sort()
    median_size = font_sizes[len(font_sizes) // 2]
    heading_threshold = median_size * 1.2  # 20% larger = heading

    # Group chars by line (y-position)
    lines_by_y = {}
    for c in chars:
        y = round(c.get("top", 0), 0)
        lines_by_y.setdefault(y, []).append(c)

    heading_texts = set()
    for y, line_chars in lines_by_y.items():
        avg_size = sum(c.get("size", 12) for c in line_chars) / len(line_chars)
        if avg_size >= heading_threshold:
            text = "".join(c.get("text", "") for c in line_chars).strip()
            if text and len(text) > 2:
                heading_texts.add(text)

    # Ensure headings are on their own line
    for heading in heading_texts:
        if heading in page_text:
            page_text = page_text.replace(heading, f"\n{heading}\n")

    return page_text


def _parse_pdf_pypdf2(file_bytes: bytes) -> Tuple[str, bool]:
    """Fallback PDF parsing using PyPDF2."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts).strip()

        if len(full_text) < 50:
            logger.info("PDF appears to be scanned (minimal text extracted). OCR needed.")
            return "", True

        return full_text, False

    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}. Will attempt OCR.")
        return "", True
