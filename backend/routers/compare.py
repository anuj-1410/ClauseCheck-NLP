"""
ClauseCheck – Compare Router
POST /api/compare — Upload two documents and compare them.
"""

import gc
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from config import MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS
from services.document_parser import parse_document
from services.ocr_service import extract_text_from_scanned_pdf
from services.language_detector import detect_language
from services.contract_comparator import compare_contracts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["compare"])


@router.post("/compare")
async def compare_documents(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare two legal documents clause-by-clause."""
    bytes1 = None
    bytes2 = None

    try:
        name1 = file1.filename or "Document 1.txt"
        name2 = file2.filename or "Document 2.txt"

        # Validate both files
        for f, label in [(file1, "File 1"), (file2, "File 2")]:
            ext = Path(f.filename or "unknown.txt").suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(400, f"{label}: Unsupported file type: {ext}")

        bytes1 = await file1.read()
        bytes2 = await file2.read()

        for b, label in [(bytes1, "File 1"), (bytes2, "File 2")]:
            if len(b) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(400, f"{label}: File too large")

        # Parse both documents
        text1, ocr1, _ = parse_document(bytes1, name1)
        text2, ocr2, _ = parse_document(bytes2, name2)

        if ocr1:
            text1 = extract_text_from_scanned_pdf(bytes1)
        _ensure_valid_extracted_text(text1, "File 1")

        if ocr2:
            text2 = extract_text_from_scanned_pdf(bytes2)
        _ensure_valid_extracted_text(text2, "File 2")

        # Detect each document language independently.
        language1 = detect_language(text1)
        language2 = detect_language(text2)

        # Compare
        result = compare_contracts(
            text1, text2,
            name1=name1,
            name2=name2,
            language1=language1,
            language2=language2,
        )

        return {"success": True, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Comparison failed: {e}")
        raise HTTPException(500, f"Comparison failed: {str(e)}")
    finally:
        bytes1 = None
        bytes2 = None
        gc.collect()


def _ensure_valid_extracted_text(text: str, label: str) -> None:
    """Reject OCR sentinel strings and empty extractions before comparison continues."""
    if isinstance(text, str) and text.startswith("[OCR Error:"):
        message = text.removeprefix("[OCR Error: ").removesuffix("]")
        raise HTTPException(status_code=422, detail=f"{label}: {message}")

    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=422, detail=f"{label}: Could not extract meaningful text.")
