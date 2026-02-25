"""
ClauseCheck – Configuration Module
Loads environment variables and defines application constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# Supabase
# ──────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ──────────────────────────────────────────────
# Tesseract OCR
# ──────────────────────────────────────────────
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
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
