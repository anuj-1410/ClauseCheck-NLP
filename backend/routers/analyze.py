"""
ClauseCheck – Analysis Router
POST /api/analyze — Full document analysis pipeline.
"""

import gc
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from config import MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS
from services.document_parser import parse_document
from services.ocr_service import extract_text_from_scanned_pdf
from services.language_detector import detect_language, get_language_name
from services.clause_segmenter import segment_clauses
from services.entity_extractor import extract_entities
from services.obligation_detector import detect_obligations
from services.risk_detector import detect_risks, calculate_overall_risk_score
from services.compliance_checker import check_compliance
from services.explanation_generator import generate_explanations
from services.summarizer import summarize_document
from db.supabase_client import store_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Full contract analysis pipeline:
    1. Validate & parse document
    2. OCR if scanned
    3. Detect language
    4. Segment clauses
    5. Extract entities
    6. Detect obligations
    7. Detect risks
    8. Check compliance
    9. Generate explanations
    10. Summarize
    11. Store results
    12. Delete raw data
    """
    file_bytes = None

    try:
        # ── Step 1: Validate file ──
        filename = file.filename or "unknown.txt"
        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file_bytes = await file.read()

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )

        logger.info(f"Processing document: {filename} ({len(file_bytes)} bytes)")

        # ── Step 2: Parse document ──
        text, needs_ocr = parse_document(file_bytes, filename)

        # ── Step 3: OCR if needed ──
        if needs_ocr:
            logger.info("Document requires OCR processing...")
            text = extract_text_from_scanned_pdf(file_bytes)

        if not text or len(text.strip()) < 20:
            raise HTTPException(
                status_code=422,
                detail="Could not extract meaningful text from the document. "
                       "Ensure the document contains readable printed text."
            )

        # ── Step 4: Detect language ──
        language = detect_language(text)
        language_name = get_language_name(language)
        logger.info(f"Language detected: {language_name}")

        # ── Step 5: Segment clauses ──
        clauses = segment_clauses(text, language)
        logger.info(f"Segmented into {len(clauses)} clauses")

        # ── Step 6: Extract entities ──
        entities = extract_entities(text, language)
        logger.info(f"Extracted entities: {sum(len(v) for v in entities.values())} total")

        # ── Step 7: Detect obligations ──
        obligations = detect_obligations(clauses, language)
        logger.info(f"Detected {len(obligations)} obligations")

        # ── Step 8: Detect risks ──
        risks = detect_risks(clauses, language)
        risk_score = calculate_overall_risk_score(risks)
        logger.info(f"Risk score: {risk_score}/100 ({len(risks)} findings)")

        # ── Step 9: Check compliance ──
        compliance = check_compliance(clauses, text, language)
        compliance_score = compliance["compliance_score"]
        logger.info(f"Compliance score: {compliance_score}/100")

        # ── Step 10: Generate explanations ──
        explanations = generate_explanations(risks, compliance, language)

        # ── Step 11: Summarize ──
        summary = summarize_document(text)

        # ── Build result payload ──
        clause_analysis = {
            "clauses": clauses,
            "entities": entities,
            "obligations": obligations,
            "risks": [
                {
                    "clause_id": r["clause_id"],
                    "risk_type": r["risk_type"],
                    "severity": r["severity"],
                    "description": r["description"],
                    "matched_text": r.get("matched_text", ""),
                    "clause_text": r.get("clause_text", "")[:300],
                    "risk_score": r["risk_score"]
                }
                for r in risks
            ],
            "compliance": compliance,
            "explanations": explanations
        }

        result_data = {
            "document_name": filename,
            "language": language_name,
            "risk_score": risk_score,
            "compliance_score": compliance_score,
            "summary": summary,
            "clause_analysis": clause_analysis
        }

        # ── Step 12: Store in database ──
        stored = store_result(result_data)
        logger.info(f"Analysis stored with ID: {stored.get('id', 'unknown')}")

        # ── Step 13: Return response ──
        return {
            "success": True,
            "id": stored.get("id"),
            "document_name": filename,
            "language": language_name,
            "risk_score": risk_score,
            "compliance_score": compliance_score,
            "summary": summary,
            "clause_analysis": clause_analysis,
            "created_at": stored.get("created_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    finally:
        # ── Step 14: Delete raw data (privacy) ──
        file_bytes = None
        gc.collect()
        logger.info("Raw document data cleared from memory.")
