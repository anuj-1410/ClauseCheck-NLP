"""
ClauseCheck – OCR Service
Uses Tesseract OCR to extract text from scanned PDF images.
Supports English and Hindi (Devanagari) text.
"""

import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# Attempt to import optional dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed. OCR will not be available.")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not installed. Scanned PDF OCR will not be available.")


def configure_tesseract(tesseract_path: str):
    """Set the Tesseract executable path."""
    if TESSERACT_AVAILABLE:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def extract_text_from_scanned_pdf(
    file_bytes: bytes,
    languages: str = "eng+hin"
) -> str:
    """
    Convert scanned PDF pages to images and OCR each page.

    Args:
        file_bytes: Raw PDF bytes
        languages: Tesseract language codes (e.g., 'eng', 'hin', 'eng+hin')

    Returns:
        Extracted text from all pages combined.
    """
    if not TESSERACT_AVAILABLE:
        logger.error("Tesseract is not available. Cannot perform OCR.")
        return "[OCR Error: Tesseract not installed]"

    if not PDF2IMAGE_AVAILABLE:
        logger.error("pdf2image is not available. Cannot convert PDF to images.")
        return "[OCR Error: pdf2image not installed]"

    try:
        images = convert_from_bytes(file_bytes, dpi=300)
        text_parts = []

        for i, image in enumerate(images):
            logger.info(f"OCR processing page {i + 1}/{len(images)}...")
            page_text = pytesseract.image_to_string(
                image,
                lang=languages,
                config="--psm 6"  # Assume uniform block of text
            )
            if page_text.strip():
                text_parts.append(page_text.strip())

        return "\n\n".join(text_parts)

    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return f"[OCR Error: {str(e)}]"


def extract_text_from_image(
    image_bytes: bytes,
    languages: str = "eng+hin"
) -> str:
    """
    OCR a single image.

    Args:
        image_bytes: Raw image bytes
        languages: Tesseract language codes

    Returns:
        Extracted text.
    """
    if not TESSERACT_AVAILABLE:
        return "[OCR Error: Tesseract not installed]"

    try:
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image, lang=languages, config="--psm 6")
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        return f"[OCR Error: {str(e)}]"
