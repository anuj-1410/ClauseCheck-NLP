"""
ClauseCheck – Language Detection Service
Multi-layer language detection:
  1. Devanagari script ratio (deterministic)
  2. fastText validation
  3. langdetect fallback
"""

import re
import logging
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)

# Make langdetect deterministic
DetectorFactory.seed = 0

# Try to load fastText language model
_ftlang = None
try:
    from fast_langdetect import detect as ft_detect_raw
    def _ft_detect_wrapper(text):
        result = ft_detect_raw(text, low_memory=True)
        # fast_langdetect returns a dict with 'lang' and 'score'
        if isinstance(result, dict):
            return result
        # Fallback: some versions return string
        return {"lang": str(result), "score": 1.0}
    _ftlang = _ft_detect_wrapper
    logger.info("fast-langdetect language detector loaded.")
except ImportError:
    logger.info("fast-langdetect not installed. Skipping fastText layer.")

# Devanagari Unicode range
_DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
_DEVANAGARI_THRESHOLD = 0.30  # 30% Devanagari chars → Hindi


def detect_language(text: str) -> str:
    """
    Detect the language of the given text using 3-layer detection:
      Layer 1: Devanagari script ratio (deterministic, fastest)
      Layer 2: fastText model validation
      Layer 3: langdetect fallback

    Returns:
        'en' for English, 'hi' for Hindi.
    """
    if not text or len(text.strip()) < 10:
        logger.warning("Text too short for reliable language detection. Defaulting to English.")
        return "en"

    # ── Layer 1: Script ratio detection (deterministic) ──
    script_result = _detect_by_script_ratio(text)
    if script_result is not None:
        logger.info(f"Script ratio detection: {script_result}")
        return script_result

    # ── Layer 2: fastText validation ──
    if _ftlang is not None:
        ft_result = _detect_with_fasttext(text)
        if ft_result is not None:
            logger.info(f"fastText detection: {ft_result}")
            return ft_result

    # ── Layer 3: langdetect fallback ──
    return _detect_with_langdetect(text)


def _detect_by_script_ratio(text: str) -> str | None:
    """
    Count Devanagari characters vs total alphabetic characters.
    If Devanagari ratio > 30%, classify as Hindi.
    Returns None if ratio is ambiguous (let other layers decide).
    """
    # Count only alphabetic/script characters (ignore digits, spaces, punctuation)
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) < 20:
        return None

    devanagari_count = len(_DEVANAGARI_RE.findall(text))
    ratio = devanagari_count / len(alpha_chars)

    if ratio > _DEVANAGARI_THRESHOLD:
        return "hi"
    elif ratio < 0.05:
        # Very clearly non-Hindi
        return "en"

    # Ambiguous range — let next layer decide
    return None


def _detect_with_fasttext(text: str) -> str | None:
    """Use fastText language identification model."""
    try:
        # ftlangdetect expects a single-line string
        clean_text = text[:5000].replace("\n", " ").strip()
        result = _ftlang(clean_text)
        lang = result.get("lang", "")
        score = result.get("score", 0)

        if score < 0.5:
            return None  # Low confidence — skip

        if lang in ("hi", "mr", "ne", "sa"):
            return "hi"
        else:
            return "en"
    except Exception as e:
        logger.warning(f"fastText detection failed: {e}")
        return None


def _detect_with_langdetect(text: str) -> str:
    """Fallback to langdetect library."""
    try:
        lang = detect(text)
        logger.info(f"langdetect result: {lang}")

        if lang in ("hi", "mr", "ne", "sa"):
            return "hi"
        else:
            return "en"
    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to English.")
        return "en"


def get_language_name(code: str) -> str:
    """Get human-readable language name."""
    return {"en": "English", "hi": "Hindi"}.get(code, "Unknown")
