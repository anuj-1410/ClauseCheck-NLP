"""
ClauseCheck – Language Detection Service
Detects whether a document is in Hindi or English using langdetect.
"""

import logging
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)

# Make detection deterministic
DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.

    Returns:
        'en' for English, 'hi' for Hindi, or detected ISO code.
    """
    if not text or len(text.strip()) < 10:
        logger.warning("Text too short for reliable language detection. Defaulting to English.")
        return "en"

    try:
        lang = detect(text)
        logger.info(f"Detected language: {lang}")

        # Map to supported languages
        if lang in ("hi", "mr", "ne", "sa"):  # Hindi and related Devanagari scripts
            return "hi"
        else:
            return "en"

    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to English.")
        return "en"


def get_language_name(code: str) -> str:
    """Get human-readable language name."""
    return {"en": "English", "hi": "Hindi"}.get(code, "Unknown")
