"""
ClauseCheck v2.0 – FastAPI Main Application
Bilingual Legal Contract Risk & Compliance Analyzer
with LLM-powered features, contract comparison, and more.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SUPABASE_URL, SUPABASE_KEY, TESSERACT_PATH, GROQ_API_KEY
from db.supabase_client import initialize as init_db
from services.ocr_service import configure_tesseract
from services.llm_service import initialize as init_llm
from routers.analyze import router as analyze_router
from routers.history import router as history_router
from routers.chat import router as chat_router
from routers.compare import router as compare_router
from routers.report import router as report_router

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("clausecheck")


# ──────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  ClauseCheck v2.0 – Starting up...")
    logger.info("=" * 60)

    # Initialize database
    init_db(SUPABASE_URL, SUPABASE_KEY)

    # Configure Tesseract
    configure_tesseract(TESSERACT_PATH)

    # Initialize LLM
    init_llm(GROQ_API_KEY)

    # Pre-load NLP models
    _preload_models()

    logger.info("✅ ClauseCheck v2.0 is ready!")
    logger.info("=" * 60)

    yield  # App is running

    logger.info("ClauseCheck shutting down...")


def _preload_models():
    """Pre-load NLP models to avoid first-request latency."""
    try:
        import spacy
        spacy.load("en_core_web_sm")
        logger.info("✅ spaCy English model loaded.")
    except Exception as e:
        logger.warning(f"spaCy model not available: {e}")
        logger.warning("  Run: python -m spacy download en_core_web_sm")


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="ClauseCheck",
    description="Bilingual Legal Contract Risk & Compliance Analyzer v2.0",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS – allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(analyze_router)
app.include_router(history_router)
app.include_router(chat_router)
app.include_router(compare_router)
app.include_router(report_router)


@app.get("/")
async def root():
    return {
        "name": "ClauseCheck",
        "version": "2.0.0",
        "description": "Bilingual Legal Contract Risk & Compliance Analyzer",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "history": "GET /api/history",
            "history_detail": "GET /api/history/{id}",
            "chat": "POST /api/chat",
            "negotiate": "POST /api/negotiate",
            "whatif": "POST /api/whatif",
            "compare": "POST /api/compare",
            "report": "GET /api/report/{id}",
            "options": "GET /api/options",
        }
    }


@app.get("/health")
async def health_check():
    from services.llm_service import is_available
    return {
        "status": "healthy",
        "version": "2.0.0",
        "llm_available": is_available(),
    }
