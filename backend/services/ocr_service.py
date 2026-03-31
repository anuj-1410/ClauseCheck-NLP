"""
ClauseCheck – OCR Service
Uses Tesseract OCR to extract text from scanned PDF images.
Supports English and Hindi (Devanagari) text.
"""

import io
import logging
from typing import Optional
import os
import re

from PIL import Image

logger = logging.getLogger(__name__)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

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
        return "[OCR Error: Tesseract not installed. Install Tesseract OCR and set TESSERACT_PATH.]"

    if not PDF2IMAGE_AVAILABLE:
        logger.error("pdf2image is not available. Cannot convert PDF to images.")
        return "[OCR Error: pdf2image not installed. Run: pip install pdf2image]"

    try:
        poppler_path = os.getenv("POPPLER_PATH")
        convert_kwargs = {"dpi": 300}
        if poppler_path:
            convert_kwargs["poppler_path"] = poppler_path
        images = convert_from_bytes(file_bytes, **convert_kwargs)
        text_parts = []
        selected_languages = _select_ocr_languages(images, default_languages=languages)
        logger.info(f"OCR language mode selected: {selected_languages}")
        sample_confidence = _estimate_ocr_confidence(images, selected_languages)
        if sample_confidence is not None:
            logger.info(f"OCR sample confidence: {sample_confidence:.1f}")
            if sample_confidence < 38:
                return (
                    "[OCR Error: Scan quality is too low for reliable analysis. "
                    "Please upload a clearer PDF (higher resolution, less compression, minimal skew).]"
                )

        for i, image in enumerate(images):
            logger.info(f"OCR processing page {i + 1}/{len(images)}...")
            try:
                page_text = pytesseract.image_to_string(
                    image,
                    lang=selected_languages,
                    config="--psm 6"  # Assume uniform block of text
                )
            except Exception as page_error:
                # If Hindi traineddata is not installed, fall back to English OCR.
                if "Failed loading language" in str(page_error) and selected_languages != "eng":
                    logger.warning("OCR language pack missing; falling back to English OCR.")
                    selected_languages = "eng"
                    page_text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config="--psm 6"
                    )
                else:
                    raise
            if page_text.strip():
                text_parts.append(page_text.strip())

        return "\n\n".join(text_parts)

    except Exception as e:
        error_text = str(e)
        if "Unable to get page count" in error_text or "poppler" in error_text.lower():
            logger.error("OCR failed because Poppler is missing or not configured.")
            return (
                "[OCR Error: Poppler is required for PDF OCR on Windows. "
                "Install Poppler and set POPPLER_PATH to the Poppler bin folder.]"
            )
        logger.error(f"OCR processing failed: {e}")
        return f"[OCR Error: {str(e)}]"


def _select_ocr_languages(images, default_languages: str = "eng+hin") -> str:
    """
    Auto-select OCR language pack from sample pages.
    Returns 'eng' for mostly Latin docs, otherwise defaults to bilingual OCR.
    """
    if not images:
        return default_languages

    sample_pages = images[: min(2, len(images))]
    sample_text_parts = []
    for sample in sample_pages:
        try:
            sample_text_parts.append(
                pytesseract.image_to_string(sample, lang=default_languages, config="--psm 6")
            )
        except Exception:
            # If sampling fails, keep default OCR mode.
            return default_languages

    sample_text = " ".join(sample_text_parts)
    alpha_chars = [c for c in sample_text if c.isalpha()]
    if len(alpha_chars) < 20:
        return default_languages

    dev_count = len(_DEVANAGARI_RE.findall(sample_text))
    dev_ratio = dev_count / len(alpha_chars)
    if dev_ratio < 0.02:
        return "eng"
    return default_languages


def _estimate_ocr_confidence(images, languages: str) -> Optional[float]:
    """
    Estimate OCR confidence using first pages.
    Returns average confidence (0-100), or None if unavailable.
    """
    if not images:
        return None

    sample_pages = images[: min(3, len(images))]
    scores = []
    for page in sample_pages:
        try:
            data = pytesseract.image_to_data(
                page,
                lang=languages,
                config="--psm 6",
                output_type=pytesseract.Output.DICT
            )
            confs = data.get("conf", [])
            texts = data.get("text", [])
            for conf, text in zip(confs, texts):
                if not text or not text.strip():
                    continue
                try:
                    val = float(conf)
                except Exception:
                    continue
                if val >= 0:
                    scores.append(val)
        except Exception:
            return None

    if not scores:
        return None
    return sum(scores) / len(scores)


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
