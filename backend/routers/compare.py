"""
ClauseCheck – Compare Router
POST /api/compare — Upload two documents and compare them.
"""

import gc
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional

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
        text1, ocr1 = parse_document(bytes1, file1.filename)
        text2, ocr2 = parse_document(bytes2, file2.filename)

        if ocr1:
            text1 = extract_text_from_scanned_pdf(bytes1)
        if ocr2:
            text2 = extract_text_from_scanned_pdf(bytes2)

        if len(text1.strip()) < 20 or len(text2.strip()) < 20:
            raise HTTPException(422, "Could not extract text from one or both documents.")

        # Detect language (use first doc's language)
        language = detect_language(text1)

        # Compare
        result = compare_contracts(
            text1, text2,
            name1=file1.filename or "Document 1",
            name2=file2.filename or "Document 2",
            language=language,
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
