"""
ClauseCheck – Configuration Module
Loads environment variables and defines application constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment flag."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    """Parse an integer environment flag."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default

# ──────────────────────────────────────────────
# Supabase
# ──────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ──────────────────────────────────────────────
# Groq LLM
# ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ──────────────────────────────────────────────
# OCR Runtime
# ──────────────────────────────────────────────
PADDLEOCR_USE_GPU = _get_bool_env("PADDLEOCR_USE_GPU", default=False)
PADDLEOCR_ENABLE_MKLDNN = _get_bool_env(
    "PADDLEOCR_ENABLE_MKLDNN",
    default=not PADDLEOCR_USE_GPU and os.name != "nt",
)
PADDLEOCR_CPU_THREADS = _get_int_env("PADDLEOCR_CPU_THREADS", default=min(8, os.cpu_count() or 4))
PADDLEOCR_MKLDNN_CACHE_CAPACITY = _get_int_env("PADDLEOCR_MKLDNN_CACHE_CAPACITY", default=10)
PADDLEOCR_TEXT_DET_LIMIT_SIDE_LEN = _get_int_env("PADDLEOCR_TEXT_DET_LIMIT_SIDE_LEN", default=960)
PADDLEOCR_TEXT_RECOGNITION_BATCH_SIZE = _get_int_env("PADDLEOCR_TEXT_RECOGNITION_BATCH_SIZE", default=8)
OCR_RENDER_DPI = _get_int_env("OCR_RENDER_DPI", default=150)
OCR_PAGE_MAX_SIDE = _get_int_env("OCR_PAGE_MAX_SIDE", default=1536)
OCR_PAGE_PARALLELISM = _get_int_env(
    "OCR_PAGE_PARALLELISM",
    default=max(1, min(4, os.cpu_count() or 1)),
)

# ──────────────────────────────────────────────
# Upload Constraints
# ──────────────────────────────────────────────
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# ──────────────────────────────────────────────
# NLP Model Flags
# ──────────────────────────────────────────────
SPACY_MODEL = "en_core_web_sm"
STANZA_LANG = "hi"
SEMANTIC_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
