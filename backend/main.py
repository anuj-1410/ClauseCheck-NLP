"""
ClauseCheck – FastAPI Main Application
Bilingual Legal Contract Risk & Compliance Analyzer
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SUPABASE_URL, SUPABASE_KEY, TESSERACT_PATH
from db.supabase_client import initialize as init_db
from services.ocr_service import configure_tesseract
from routers.analyze import router as analyze_router
from routers.history import router as history_router

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
    logger.info("  ClauseCheck – Starting up...")
    logger.info("=" * 60)

    # Initialize database
    init_db(SUPABASE_URL, SUPABASE_KEY)

    # Configure Tesseract
    configure_tesseract(TESSERACT_PATH)

    # Pre-load NLP models
    _preload_models()

    logger.info("✅ ClauseCheck is ready!")
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

    # Stanza is loaded lazily on first Hindi document


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="ClauseCheck",
    description="Bilingual Legal Contract Risk & Compliance Analyzer",
    version="1.0.0",
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


@app.get("/")
async def root():
    return {
        "name": "ClauseCheck",
        "version": "1.0.0",
        "description": "Bilingual Legal Contract Risk & Compliance Analyzer",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "history": "GET /api/history",
            "history_detail": "GET /api/history/{id}",
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
