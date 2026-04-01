"""
ClauseCheck – OCR Service
Uses PaddleOCR to extract text from scanned PDF images.
Supports English and Hindi (Devanagari) text.
"""

import io
import inspect
import logging
import os
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# PaddleX performs an online model-source probe during import unless this is set.
# Defaulting it here keeps local/offline startup predictable while still allowing
# an explicit environment override.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PaddleOCR = None
    PADDLEOCR_AVAILABLE = False
    logger.warning("paddleocr not installed. OCR will not be available.")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed. PDF OCR will not be available.")


_OCR_ENGINES: Dict[str, object] = {}
_OCR_OPTIONS = {
    "use_gpu": False,
    "use_angle_cls": False,
    "show_log": False,
}
_PADDLEOCR_INIT_PARAMS: Optional[set[str]] = None
_PDF_RENDER_DPI = 200
_OCR_PREVIEW_MAX_SIDE = 1400
_OCR_PAGE_MAX_SIDE = 2200
_OCR_LANGUAGE_SAMPLE_PAGES = 1
_LANGUAGE_ALIASES = {
    "eng": "en",
    "english": "en",
    "en": "en",
    # PaddleOCR accepts `lang="hi"` and internally maps it to the Devanagari model.
    "hin": "hi",
    "hi": "hi",
    "hindi": "hi",
    "devanagari": "hi",
    "eng+hin": "en,hi",
    "eng+hi": "en,hi",
    "en+hi": "en,hi",
}


def configure_paddleocr(
    use_gpu: bool = False,
    use_angle_cls: bool = False,
    show_log: bool = False,
) -> None:
    """Configure the lazy-loaded PaddleOCR engine registry."""
    next_options = {
        "use_gpu": use_gpu,
        "use_angle_cls": use_angle_cls,
        "show_log": show_log,
    }

    if next_options != _OCR_OPTIONS:
        _OCR_ENGINES.clear()
        _OCR_OPTIONS.update(next_options)

    logger.info(
        "PaddleOCR configured (use_gpu=%s, use_angle_cls=%s)",
        _OCR_OPTIONS["use_gpu"],
        _OCR_OPTIONS["use_angle_cls"],
    )


def extract_text_from_scanned_pdf(
    file_bytes: bytes,
    languages: str = "eng+hin",
) -> str:
    """
    Convert scanned PDF pages to images and OCR each page with PaddleOCR.

    Args:
        file_bytes: Raw PDF bytes
        languages: Preferred OCR language hints. Legacy values such as 'eng',
            'hin', and 'eng+hin' are mapped to PaddleOCR equivalents.

    Returns:
        Extracted text from all pages combined.
    """
    if not PADDLEOCR_AVAILABLE:
        logger.error("PaddleOCR is not available. Cannot perform OCR.")
        return "[OCR Error: PaddleOCR not installed. Install paddleocr and paddlepaddle.]"

    if not PYMUPDF_AVAILABLE:
        logger.error("PyMuPDF is not available. Cannot render PDF pages for OCR.")
        return "[OCR Error: PyMuPDF not installed. Install PyMuPDF to enable PDF OCR.]"

    try:
        started_at = time.perf_counter()
        images = _render_pdf_to_images(file_bytes, dpi=_PDF_RENDER_DPI)
        if not images:
            return "[OCR Error: No pages could be rendered for OCR.]"

        logger.info("Rendered %s PDF page(s) for OCR at %s DPI.", len(images), _PDF_RENDER_DPI)

        preview_images = [
            _prepare_image_for_ocr(image, max_side=_OCR_PREVIEW_MAX_SIDE)
            for image in images[:_OCR_LANGUAGE_SAMPLE_PAGES]
        ]

        ranked_languages = _rank_ocr_languages(preview_images, languages)
        logger.info("OCR language order selected: %s", ", ".join(ranked_languages))

        text_parts = []
        for index, image in enumerate(images):
            logger.info("OCR processing page %s/%s...", index + 1, len(images))
            page_started_at = time.perf_counter()
            prepared_image = _prepare_image_for_ocr(image, max_side=_OCR_PAGE_MAX_SIDE)
            page_text = _ocr_page_with_fallback(prepared_image, ranked_languages)
            if page_text:
                text_parts.append(page_text)
            logger.info(
                "OCR finished page %s/%s in %.1fs (%s characters).",
                index + 1,
                len(images),
                time.perf_counter() - page_started_at,
                len(page_text),
            )

        if not text_parts:
            return "[OCR Error: PaddleOCR could not extract readable text from this PDF.]"

        logger.info(
            "OCR extracted text from %s/%s page(s) in %.1fs.",
            len(text_parts),
            len(images),
            time.perf_counter() - started_at,
        )

        return "\n\n".join(text_parts)

    except Exception as exc:
        logger.error("OCR processing failed: %s", exc)
        return f"[OCR Error: {str(exc)}]"


def extract_text_from_image(
    image_bytes: bytes,
    languages: str = "eng+hin",
) -> str:
    """
    OCR a single image with PaddleOCR.

    Args:
        image_bytes: Raw image bytes
        languages: Preferred OCR language hints.

    Returns:
        Extracted text.
    """
    if not PADDLEOCR_AVAILABLE:
        return "[OCR Error: PaddleOCR not installed]"

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        preview_image = _prepare_image_for_ocr(image, max_side=_OCR_PREVIEW_MAX_SIDE)
        ranked_languages = _rank_ocr_languages([preview_image], languages)
        page_text = _ocr_page_with_fallback(
            _prepare_image_for_ocr(image, max_side=_OCR_PAGE_MAX_SIDE),
            ranked_languages,
        )
        if page_text:
            return page_text
        return "[OCR Error: PaddleOCR could not extract readable text from this image.]"
    except Exception as exc:
        logger.error("Image OCR failed: %s", exc)
        return f"[OCR Error: {str(exc)}]"


def _render_pdf_to_images(file_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    """Render PDF pages to RGB images using PyMuPDF, with no Poppler dependency."""
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not installed")

    document = fitz.open(stream=file_bytes, filetype="pdf")
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    images: List[Image.Image] = []

    try:
        for page in document:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )
            images.append(image)
    finally:
        document.close()

    return images


def _prepare_image_for_ocr(image: Image.Image, max_side: int) -> Image.Image:
    """Resize very large images before OCR to keep CPU inference time bounded."""
    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= max_side:
        return image

    scale = max_side / longest_side
    resized_size = (
        max(1, int(width * scale)),
        max(1, int(height * scale)),
    )
    return image.resize(resized_size, Image.Resampling.LANCZOS)


def _get_ocr_engine(language: str):
    """Get or create a PaddleOCR engine for the requested language."""
    normalized_language = _LANGUAGE_ALIASES.get(language.lower(), language.lower())

    if normalized_language not in _OCR_ENGINES:
        if not PADDLEOCR_AVAILABLE:
            raise RuntimeError("PaddleOCR is not installed")

        try:
            _OCR_ENGINES[normalized_language] = PaddleOCR(
                **_build_engine_kwargs(normalized_language)
            )
            logger.info("PaddleOCR model loaded for language '%s'.", normalized_language)
        except Exception as exc:
            raise RuntimeError(
                f"PaddleOCR initialization failed for language '{normalized_language}': {exc}"
            ) from exc

    return _OCR_ENGINES[normalized_language]


def _normalize_language_candidates(languages: str | Iterable[str]) -> List[str]:
    """Normalize old and new OCR language hints into PaddleOCR language codes."""
    raw_values = [languages] if isinstance(languages, str) else list(languages)
    candidates: List[str] = []

    for raw_value in raw_values:
        mapped_value = _LANGUAGE_ALIASES.get(str(raw_value).strip().lower(), str(raw_value).strip())
        for token in re.split(r"[+,]", mapped_value):
            normalized = token.strip().lower()
            if not normalized:
                continue
            normalized = _LANGUAGE_ALIASES.get(normalized, normalized)
            if normalized and normalized not in candidates:
                candidates.append(normalized)

    return candidates or ["en", "hi"]


def _rank_ocr_languages(images, languages: str | Iterable[str]) -> List[str]:
    """Rank OCR language candidates by confidence and script match on sample pages."""
    candidates = _normalize_language_candidates(languages)
    if len(candidates) <= 1 or not images:
        return candidates

    sample_pages = images[: min(_OCR_LANGUAGE_SAMPLE_PAGES, len(images))]

    # Fast path for the common bilingual setting on CPU-heavy local setups:
    # try English first and only pay the Hindi sampling cost if English looks weak.
    if len(candidates) == 2 and set(candidates) == {"en", "hi"}:
        english_lines = []
        for sample_page in sample_pages:
            try:
                english_lines.extend(_run_ocr(sample_page, "en"))
            except Exception as exc:
                logger.warning("English OCR sampling failed: %s", exc)
                english_lines = []
                break

        english_score = _score_language_sample(english_lines, "en")
        if english_score >= 0.55:
            logger.info("English OCR sample score %.2f is strong enough to skip Hindi pre-sampling.", english_score)
            return ["en", "hi"]

    scored_candidates: List[Tuple[str, float]] = []

    for candidate in candidates:
        sample_lines = []
        for sample_page in sample_pages:
            try:
                sample_lines.extend(_run_ocr(sample_page, candidate))
            except Exception as exc:
                logger.warning("OCR language sampling failed for '%s': %s", candidate, exc)
                sample_lines = []
                break

        scored_candidates.append((candidate, _score_language_sample(sample_lines, candidate)))

    scored_candidates.sort(key=lambda item: item[1], reverse=True)
    return [candidate for candidate, _ in scored_candidates]


def _estimate_ocr_confidence(images, language: str) -> Optional[float]:
    """Estimate average OCR confidence on the first few pages."""
    if not images:
        return None

    sample_pages = images[: min(3, len(images))]
    scores = []

    for sample_page in sample_pages:
        try:
            lines = _run_ocr(sample_page, language)
        except Exception:
            return None

        for line in lines:
            text = line.get("text", "")
            confidence = line.get("confidence")
            if text and confidence is not None:
                scores.append(confidence)

    if not scores:
        return None
    return sum(scores) / len(scores)


def _ocr_page_with_fallback(image: Image.Image, language_order: List[str]) -> str:
    """OCR a page and fall back to alternate languages if the primary output is weak."""
    best_text = ""
    best_score = 0.0

    for index, language in enumerate(language_order):
        page_text, score = _extract_page_text_and_score(image, language)
        if page_text and score > best_score:
            best_text = page_text
            best_score = score

        if index == 0 and page_text and score >= 0.55:
            break

    return best_text.strip()


def _extract_page_text_and_score(image: Image.Image, language: str) -> Tuple[str, float]:
    """Run OCR for one language and return page text plus a quality score."""
    lines = _run_ocr(image, language)
    page_text = "\n".join(line["text"] for line in lines if line.get("text")).strip()
    return page_text, _score_language_sample(lines, language)


def _run_ocr(image: Image.Image, language: str) -> List[Dict[str, Optional[float]]]:
    """Run PaddleOCR on a PIL image and normalize the result structure."""
    engine = _get_ocr_engine(language)
    image_array = np.ascontiguousarray(np.asarray(image.convert("RGB")))
    result = _invoke_ocr(engine, image_array)

    lines: List[Dict[str, Optional[float]]] = []
    _collect_result_lines(result, lines)
    return lines


def _build_engine_kwargs(language: str) -> Dict[str, object]:
    """Build PaddleOCR constructor kwargs compatible with installed versions."""
    init_params = _get_paddleocr_init_params()
    supports_modern_api = _supports_modern_paddleocr_api(init_params)
    use_gpu = _OCR_OPTIONS["use_gpu"]
    engine_kwargs: Dict[str, object] = {"lang": language}
    use_explicit_cpu_models = False

    if "device" in init_params or supports_modern_api:
        engine_kwargs["device"] = "gpu" if use_gpu else "cpu"
    elif "use_gpu" in init_params:
        engine_kwargs["use_gpu"] = use_gpu

    if not use_gpu and ("enable_mkldnn" in init_params or supports_modern_api):
        engine_kwargs["enable_mkldnn"] = False

    # PaddleOCR 3.x defaults to the server detector for PP-OCRv5. The mobile
    # detector is materially faster on local CPU inference for scanned contracts.
    if not use_gpu and "text_detection_model_name" in init_params:
        engine_kwargs["text_detection_model_name"] = "PP-OCRv5_mobile_det"
        use_explicit_cpu_models = True

    if not use_gpu and "text_recognition_model_name" in init_params:
        if language == "en":
            engine_kwargs["text_recognition_model_name"] = "en_PP-OCRv5_mobile_rec"
            use_explicit_cpu_models = True
        elif language == "hi":
            engine_kwargs["text_recognition_model_name"] = "devanagari_PP-OCRv5_mobile_rec"
            use_explicit_cpu_models = True

    if use_explicit_cpu_models:
        engine_kwargs.pop("lang", None)

    if "use_doc_orientation_classify" in init_params:
        engine_kwargs["use_doc_orientation_classify"] = False

    if "use_doc_unwarping" in init_params:
        engine_kwargs["use_doc_unwarping"] = False

    if "use_textline_orientation" in init_params:
        engine_kwargs["use_textline_orientation"] = _OCR_OPTIONS["use_angle_cls"]
    elif "use_angle_cls" in init_params:
        engine_kwargs["use_angle_cls"] = _OCR_OPTIONS["use_angle_cls"]

    if "show_log" in init_params:
        engine_kwargs["show_log"] = _OCR_OPTIONS["show_log"]

    return engine_kwargs


def _get_paddleocr_init_params() -> set[str]:
    """Cache PaddleOCR init parameters so we can support v2 and v3 APIs."""
    global _PADDLEOCR_INIT_PARAMS

    if _PADDLEOCR_INIT_PARAMS is None:
        try:
            _PADDLEOCR_INIT_PARAMS = set(inspect.signature(PaddleOCR.__init__).parameters)
        except (TypeError, ValueError):
            _PADDLEOCR_INIT_PARAMS = set()

    return _PADDLEOCR_INIT_PARAMS


def _supports_modern_paddleocr_api(init_params: set[str]) -> bool:
    """Detect PaddleOCR v3-style APIs that expose runtime args via **kwargs."""
    return "use_textline_orientation" in init_params and "use_gpu" not in init_params


def _invoke_ocr(engine: object, image_array: np.ndarray):
    """Invoke PaddleOCR across supported API generations."""
    predict = getattr(engine, "predict", None)
    if callable(predict):
        try:
            return predict(
                image_array,
                use_textline_orientation=_OCR_OPTIONS["use_angle_cls"],
            )
        except TypeError:
            return predict(image_array)

    return engine.ocr(image_array, cls=_OCR_OPTIONS["use_angle_cls"])


def _collect_result_lines(payload: object, lines: List[Dict[str, Optional[float]]]) -> None:
    """Recursively normalize multiple PaddleOCR result formats into text/confidence pairs."""
    if payload is None:
        return

    if isinstance(payload, dict):
        if isinstance(payload.get("rec_texts"), list):
            rec_scores = payload.get("rec_scores") or []
            for index, text in enumerate(payload.get("rec_texts", [])):
                score = rec_scores[index] if index < len(rec_scores) else None
                _append_line(lines, text, score)
            return

        text = payload.get("rec_text") or payload.get("text")
        if text:
            _append_line(lines, text, payload.get("rec_score") or payload.get("score"))

        for key in ("res", "results", "data"):
            nested = payload.get(key)
            if isinstance(nested, (list, tuple)):
                for item in nested:
                    _collect_result_lines(item, lines)
        return

    if isinstance(payload, (list, tuple)):
        if len(payload) >= 2 and isinstance(payload[1], (list, tuple)) and payload[1]:
            _append_line(lines, payload[1][0], payload[1][1] if len(payload[1]) > 1 else None)
            return

        if len(payload) >= 2 and isinstance(payload[0], str):
            _append_line(lines, payload[0], payload[1])
            return

        for item in payload:
            _collect_result_lines(item, lines)


def _append_line(
    lines: List[Dict[str, Optional[float]]],
    text: object,
    confidence: object,
) -> None:
    """Append a normalized OCR line if it contains readable text."""
    clean_text = str(text).strip()
    if not clean_text:
        return

    lines.append({
        "text": clean_text,
        "confidence": _safe_float(confidence),
    })


def _safe_float(value: object) -> Optional[float]:
    """Convert a confidence score to float if possible."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_language_sample(lines: List[Dict[str, Optional[float]]], language: str) -> float:
    """Score how well a candidate OCR language matches the extracted sample."""
    if not lines:
        return 0.0

    confidences = [line["confidence"] for line in lines if line.get("confidence") is not None]
    confidence_score = sum(confidences) / len(confidences) if confidences else 0.45

    combined_text = " ".join(line["text"] for line in lines if line.get("text"))
    alpha_chars = [char for char in combined_text if char.isalpha()]
    text_length_score = min(len(combined_text) / 400, 1.0)

    if alpha_chars:
        devanagari_ratio = len(_DEVANAGARI_RE.findall(combined_text)) / len(alpha_chars)
        if language == "hi":
            script_score = 1.0 if devanagari_ratio >= 0.15 else 0.15
        else:
            script_score = 1.0 if devanagari_ratio < 0.15 else 0.15
    else:
        script_score = 0.5

    return (confidence_score * 0.65) + (text_length_score * 0.20) + (script_score * 0.15)
