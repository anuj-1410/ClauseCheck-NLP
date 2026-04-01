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
