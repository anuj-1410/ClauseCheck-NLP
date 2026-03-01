"""
ClauseCheck – Analysis Router (v2.0)
POST /api/analyze — Full document analysis pipeline with all new features.
GET  /api/options  — Available jurisdictions and contract types.
"""

import gc
import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

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
from services.responsibility_detector import detect_responsibility_issues
from services.timeline_extractor import extract_timeline
from services.jurisdiction_engine import (
    get_jurisdiction_rules, get_contract_type_info,
    get_available_jurisdictions, get_available_contract_types,
    get_legal_references, adjust_risk_severity,
)
from services.llm_service import (
    translate_to_plain_english, generate_smart_summary, is_available as llm_available
)
from db.supabase_client import store_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/options")
async def get_analysis_options():
    """Return available jurisdictions and contract types."""
    return {
        "jurisdictions": get_available_jurisdictions(),
        "contract_types": get_available_contract_types(),
        "llm_available": llm_available(),
    }


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    jurisdiction: Optional[str] = Form("general"),
    contract_type: Optional[str] = Form("general"),
):
    """
    Full contract analysis pipeline (v2.0):
    1.  Validate & parse document
    2.  OCR if scanned
    3.  Detect language
    4.  Segment clauses
    5.  Extract entities
    6.  Detect obligations
    7.  Detect risks (with confidence scores)
    8.  Check compliance (jurisdiction-aware)
    9.  Responsibility & ambiguity analysis
    10. Timeline extraction
    11. Generate explanations (with legal refs)
    12. Plain English translations (LLM)
    13. Smart summarization (LLM)
    14. Store results
    15. Delete raw data
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

        logger.info(f"Processing: {filename} ({len(file_bytes)} bytes) | Jurisdiction: {jurisdiction} | Type: {contract_type}")

        # ── Step 2: Parse document ──
        text, needs_ocr = parse_document(file_bytes, filename)

        # ── Step 3: OCR if needed ──
        if needs_ocr:
            logger.info("Document requires OCR processing...")
            text = extract_text_from_scanned_pdf(file_bytes)

        if not text or len(text.strip()) < 20:
            raise HTTPException(
                status_code=422,
                detail="Could not extract meaningful text from the document."
            )

        # ── Step 4: Detect language ──
        language = detect_language(text)
        language_name = get_language_name(language)

        # ── Step 5: Segment clauses ──
        clauses = segment_clauses(text, language)

        # ── Step 6: Extract entities ──
        entities = extract_entities(text, language)

        # ── Step 7: Detect obligations ──
        obligations = detect_obligations(clauses, language)

        # ── Step 8: Detect risks (with confidence) ──
        risks = detect_risks(clauses, language)
        # Add confidence scores to risks
        for r in risks:
            r["confidence"] = _calculate_risk_confidence(r)
        # Adjust risk severity based on jurisdiction
        risks = adjust_risk_severity(risks, jurisdiction or "general")
        risk_score = calculate_overall_risk_score(risks)

        # ── Step 9: Jurisdiction-aware compliance ──
        jurisdiction_rules = get_jurisdiction_rules(jurisdiction or "general")
        contract_info = get_contract_type_info(contract_type or "general")
        compliance = check_compliance(clauses, text, language)

        # Add legal references from jurisdiction
        for detail in compliance.get("details", []):
            clause_type = detail.get("clause_type", "")
            req = jurisdiction_rules.get("required_clauses", {}).get(clause_type, {})
            detail["legal_reference"] = req.get("ref", "")

        # Add jurisdiction risk notes
        for r in risks:
            ref = get_legal_references(jurisdiction or "general", r["risk_type"])
            r["legal_note"] = ref

        # ── Step 10: Responsibility & ambiguity ──
        responsibility = detect_responsibility_issues(clauses, language)

        # ── Step 11: Timeline extraction ──
        timeline = extract_timeline(clauses, entities, obligations)

        # ── Step 12: Generate explanations ──
        explanations = generate_explanations(risks, compliance, language)

        # ── Step 13: Plain English translations (LLM) ──
        plain_english = []
        if llm_available():
            # Translate top 15 clauses (to stay within rate limits)
            for clause in clauses[:15]:
                try:
                    simplified = translate_to_plain_english(clause["text"], language)
                    plain_english.append({
                        "clause_id": clause["id"],
                        "original": clause["text"][:300],
                        "simplified": simplified,
                    })
                except Exception as e:
                    logger.warning(f"LLM translation failed for clause {clause['id']}: {e}")
                    plain_english.append({
                        "clause_id": clause["id"],
                        "original": clause["text"][:300],
                        "simplified": "[Translation unavailable]",
                    })

        # ── Step 14: Smart summary (LLM) ──
        if llm_available():
            try:
                summary = generate_smart_summary(text, language)
            except Exception:
                summary = summarize_document(text)
        else:
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
                    "risk_score": r["risk_score"],
                    "confidence": r.get("confidence", 0.7),
                    "legal_note": r.get("legal_note", ""),
                    "detection_method": r.get("detection_method", "pattern"),
                    "jurisdiction_note": r.get("jurisdiction_note", ""),
                }
                for r in risks
            ],
            "compliance": compliance,
            "explanations": explanations,
            "responsibility": responsibility,
            "timeline": timeline,
            "plain_english": plain_english,
            "jurisdiction": {
                "code": jurisdiction or "general",
                "name": jurisdiction_rules.get("name", "General"),
                "laws": jurisdiction_rules.get("laws", {}),
            },
            "contract_type": {
                "code": contract_type or "general",
                "name": contract_info.get("name", "General Contract"),
            },
        }

        result_data = {
            "document_name": filename,
            "language": language_name,
            "risk_score": risk_score,
            "compliance_score": compliance["compliance_score"],
            "summary": summary,
            "clause_analysis": clause_analysis,
        }

        # ── Step 15: Store ──
        stored = store_result(result_data)
        logger.info(f"✅ Analysis complete: {stored.get('id')}")

        return {
            "success": True,
            "id": stored.get("id"),
            "document_name": filename,
            "language": language_name,
            "risk_score": risk_score,
            "compliance_score": compliance["compliance_score"],
            "summary": summary,
            "clause_analysis": clause_analysis,
            "created_at": stored.get("created_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        file_bytes = None
        gc.collect()


def _calculate_risk_confidence(risk: Dict) -> float:
    """Calculate confidence score for a risk finding."""
    base = 0.7
    # Exact keyword match = higher confidence
    if risk.get("matched_text"):
        base += 0.1
    # Risk type with well-defined patterns = higher confidence
    high_conf_types = {"unlimited_liability", "one_sided_termination", "auto_renewal"}
    if risk.get("risk_type") in high_conf_types:
        base += 0.1
    return min(round(base, 2), 0.95)

