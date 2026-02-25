"""
ClauseCheck – Compliance Checking Service
Checks contracts against a predefined set of essential legal clauses
and generates a compliance score (0–100).
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Essential clause checklist for legal contracts
# ──────────────────────────────────────────────
ESSENTIAL_CLAUSES = {
    "termination": {
        "keywords": [
            "terminat", "end of agreement", "expiry", "expiration",
            "cessation", "cancellation"
        ],
        "weight": 10,
        "description": "Termination clause – defines how the contract can be ended"
    },
    "liability": {
        "keywords": [
            "liabilit", "liable", "limitation of liability", "cap on liability",
            "responsible", "responsibility"
        ],
        "weight": 10,
        "description": "Liability clause – defines liability limits and scope"
    },
    "indemnity": {
        "keywords": [
            "indemnif", "indemnity", "hold harmless", "compensat"
        ],
        "weight": 8,
        "description": "Indemnity clause – protection against third-party claims"
    },
    "confidentiality": {
        "keywords": [
            "confidential", "non-disclosure", "nda", "proprietary information",
            "trade secret"
        ],
        "weight": 9,
        "description": "Confidentiality clause – protects sensitive information"
    },
    "governing_law": {
        "keywords": [
            "governing law", "applicable law", "governed by", "laws of",
            "jurisdiction", "legal framework"
        ],
        "weight": 8,
        "description": "Governing law clause – specifies applicable legal jurisdiction"
    },
    "dispute_resolution": {
        "keywords": [
            "dispute", "arbitration", "mediation", "resolution",
            "litigation", "court", "tribunal"
        ],
        "weight": 9,
        "description": "Dispute resolution clause – defines how disputes are handled"
    },
    "force_majeure": {
        "keywords": [
            "force majeure", "act of god", "unforeseeable", "beyond control",
            "natural disaster", "pandemic", "extraordinary circumstances"
        ],
        "weight": 7,
        "description": "Force majeure clause – handles unforeseeable events"
    },
    "payment_terms": {
        "keywords": [
            "payment", "compensation", "fee", "price", "cost",
            "invoice", "billing", "remuneration", "consideration"
        ],
        "weight": 9,
        "description": "Payment terms – financial obligations and schedules"
    },
    "notice": {
        "keywords": [
            "notice", "notification", "written notice", "notify",
            "communication", "inform in writing"
        ],
        "weight": 6,
        "description": "Notice clause – how parties communicate formally"
    },
    "amendment": {
        "keywords": [
            "amend", "modification", "modify", "change",
            "variation", "alter", "supplement"
        ],
        "weight": 6,
        "description": "Amendment clause – how the contract can be changed"
    },
    "intellectual_property": {
        "keywords": [
            "intellectual property", "ip rights", "copyright", "patent",
            "trademark", "ownership of work", "work product"
        ],
        "weight": 7,
        "description": "IP clause – defines intellectual property ownership"
    },
    "warranties": {
        "keywords": [
            "warrant", "representation", "guarantee", "assurance",
            "covenant", "undertaking"
        ],
        "weight": 7,
        "description": "Warranties clause – promises about quality and accuracy"
    },
}

# Hindi essential clause keywords
HINDI_ESSENTIAL_CLAUSES = {
    "termination": {
        "keywords": ["समाप्ति", "अवधि", "रद्द", "निरस्त"],
        "weight": 10,
        "description": "समाप्ति खंड – अनुबंध कैसे समाप्त किया जा सकता है"
    },
    "liability": {
        "keywords": ["दायित्व", "जिम्मेदारी", "उत्तरदायित्व"],
        "weight": 10,
        "description": "दायित्व खंड – दायित्व सीमा और दायरे को परिभाषित करता है"
    },
    "confidentiality": {
        "keywords": ["गोपनीयता", "गोपनीय", "गुप्त"],
        "weight": 9,
        "description": "गोपनीयता खंड – संवेदनशील जानकारी की रक्षा करता है"
    },
    "dispute_resolution": {
        "keywords": ["विवाद", "मध्यस्थता", "समाधान", "न्यायालय"],
        "weight": 9,
        "description": "विवाद समाधान खंड – विवादों को कैसे संभाला जाता है"
    },
    "payment_terms": {
        "keywords": ["भुगतान", "शुल्क", "मूल्य", "राशि", "पारिश्रमिक"],
        "weight": 9,
        "description": "भुगतान शर्तें – वित्तीय दायित्व और अनुसूचियां"
    },
}


def check_compliance(
    clauses: List[Dict],
    full_text: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Check document compliance against essential clause checklist.

    Returns:
        Dict with:
        - compliance_score: 0-100
        - found_clauses: list of detected essential clauses
        - missing_clauses: list of missing essential clauses
        - details: per-clause compliance info
    """
    checklist = HINDI_ESSENTIAL_CLAUSES if language == "hi" else ESSENTIAL_CLAUSES
    text_lower = full_text.lower()

    found = []
    missing = []
    details = []

    total_weight = sum(c["weight"] for c in checklist.values())
    earned_weight = 0

    for clause_name, config in checklist.items():
        is_found, matched_keyword = _check_clause_presence(
            text_lower, config["keywords"]
        )

        detail = {
            "clause_type": clause_name,
            "description": config["description"],
            "weight": config["weight"],
            "found": is_found,
            "matched_keyword": matched_keyword
        }

        if is_found:
            found.append(clause_name)
            earned_weight += config["weight"]
        else:
            missing.append({
                "clause_type": clause_name,
                "description": config["description"],
                "importance": _weight_to_importance(config["weight"])
            })

        details.append(detail)

    # Calculate compliance score
    score = int((earned_weight / total_weight) * 100) if total_weight > 0 else 0

    result = {
        "compliance_score": score,
        "found_clauses": found,
        "missing_clauses": missing,
        "details": details,
        "total_checked": len(checklist),
        "total_found": len(found),
        "total_missing": len(missing)
    }

    logger.info(
        f"Compliance check: {len(found)}/{len(checklist)} clauses found. "
        f"Score: {score}/100"
    )

    return result


def _check_clause_presence(
    text_lower: str,
    keywords: List[str]
) -> Tuple[bool, str]:
    """Check if any keyword from the list appears in the text."""
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True, keyword
    return False, ""


def _weight_to_importance(weight: int) -> str:
    """Convert weight to importance label."""
    if weight >= 9:
        return "critical"
    elif weight >= 7:
        return "important"
    else:
        return "recommended"
