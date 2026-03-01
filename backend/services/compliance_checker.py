"""
ClauseCheck – Compliance Checking Service
Checks contracts against a predefined set of essential legal clauses
and generates a compliance score (0–100).

Upgrades:
  - Structural validation: presence is not enough, now checks clause quality
  - For each clause type, validates specific structural elements
  - Hindi structural validators for key clauses
  - Compliance = presence × quality (not just keyword detection)
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

# ──────────────────────────────────────────────
# Structural quality validators per clause type
# ──────────────────────────────────────────────
STRUCTURAL_VALIDATORS = {
    "termination": {
        "checks": [
            {"name": "notice_defined", "patterns": [
                r"(?:notice|prior\s+notice|written\s+notice)\s+(?:of\s+)?\d+\s*(?:days?|weeks?|months?)",
                r"\d+\s*(?:days?|weeks?|months?)\s*(?:prior\s+)?(?:written\s+)?notice",
            ], "label": "Notice period defined"},
            {"name": "mutual", "patterns": [
                r"(?:either|both|any)\s+party",
                r"mutual(?:ly)?",
                r"(?:by\s+)?(?:either|any)\s+(?:of\s+the\s+)?part(?:y|ies)",
            ], "label": "Mutual termination right"},
            {"name": "cure_period", "patterns": [
                r"(?:cure|remedy|rectif)\w*\s+(?:period|within|of)",
                r"(?:opportunity|right)\s+to\s+(?:cure|remedy|rectif)",
            ], "label": "Cure period specified"},
            {"name": "grounds", "patterns": [
                r"(?:for\s+cause|material\s+breach|grounds?\s+(?:for|of)|reason\s+(?:for|of))",
                r"(?:breach|default|failure|violation)\s+(?:of|to)",
            ], "label": "Termination grounds specified"},
        ],
        "weight_factor": 0.6,  # How much quality affects the score
    },
    "liability": {
        "checks": [
            {"name": "cap_defined", "patterns": [
                r"(?:cap|limit|limitation|ceiling|maximum)\s+(?:of|on|to)\s+(?:liability|damages)",
                r"(?:liability|damages)\s+(?:shall\s+)?(?:not\s+exceed|be\s+limited\s+to|capped\s+at)",
                r"(?:aggregate|total|maximum)\s+(?:liability|damages)",
            ], "label": "Liability cap defined"},
            {"name": "exclusions", "patterns": [
                r"(?:exclud|except|carve[- ]out)\w*\s+(?:from\s+)?(?:liability|limitation)",
                r"(?:indirect|consequential|incidental|special|punitive)\s+damages",
            ], "label": "Liability exclusions specified"},
        ],
        "weight_factor": 0.5,
    },
    "confidentiality": {
        "checks": [
            {"name": "duration", "patterns": [
                r"(?:confidential\w*\s+)?(?:obligat\w+\s+)?(?:shall\s+)?(?:survive|continue|remain)\s+(?:for|until|during)",
                r"(?:period|term|duration)\s+of\s+(?:confidential|non-disclos)",
                r"\d+\s*(?:years?|months?)\s+(?:after|following|from)",
            ], "label": "Confidentiality duration defined"},
            {"name": "scope", "patterns": [
                r"(?:defin\w+\s+(?:of\s+)?|means?\s+)?(?:confidential\s+information)",
                r"(?:includes?\s+(?:but\s+is\s+)?(?:not\s+)?limited\s+to)",
            ], "label": "Scope of confidential information defined"},
            {"name": "return_obligations", "patterns": [
                r"(?:return|destroy|delete)\s+(?:all\s+)?(?:confidential|materials?|documents?|copies)",
            ], "label": "Return/destruction obligations specified"},
        ],
        "weight_factor": 0.4,
    },
    "dispute_resolution": {
        "checks": [
            {"name": "mechanism", "patterns": [
                r"(?:arbitration|mediation|conciliation|negotiation)",
            ], "label": "Resolution mechanism specified"},
            {"name": "venue", "patterns": [
                r"(?:seat|venue|place|location)\s+(?:of|for)\s+(?:arbitration|proceedings|disputes?)",
                r"(?:courts?\s+(?:of|in|at)|jurisdiction\s+(?:of|in))\s+\w+",
            ], "label": "Venue/seat specified"},
        ],
        "weight_factor": 0.4,
    },
    "payment_terms": {
        "checks": [
            {"name": "amount", "patterns": [
                r"(?:Rs\.?|INR|₹|USD|\$|€)\s*[\d,]+",
                r"(?:fee|amount|price|rate|cost|compensation)\s+(?:of|is|shall\s+be|equals?)\s+",
            ], "label": "Payment amount specified"},
            {"name": "schedule", "patterns": [
                r"(?:due|payable|paid)\s+(?:within|on|by|before)\s+",
                r"(?:monthly|quarterly|annually|bi-weekly|weekly)\s+(?:payment|installment|basis)",
                r"(?:net\s+)?\d+\s*(?:days?)",
            ], "label": "Payment schedule defined"},
        ],
        "weight_factor": 0.4,
    },
}

# Hindi structural validators
HINDI_STRUCTURAL_VALIDATORS = {
    "termination": {
        "checks": [
            {"name": "notice_defined", "patterns": [
                r"सूचना\s+(?:अवधि|की\s+अवधि)",
                r"\d+\s*(?:दिन|सप्ताह|महीने)\s*(?:की\s+)?(?:पूर्व\s+)?सूचना",
            ], "label": "सूचना अवधि परिभाषित"},
            {"name": "mutual", "patterns": [
                r"(?:दोनों|किसी\s+भी)\s+पक्ष",
                r"पारस्परिक\s+(?:अधिकार|सहमति)",
            ], "label": "पारस्परिक अधिकार"},
            {"name": "grounds", "patterns": [
                r"कारण\s+(?:से|के\s+(?:लिए|आधार\s+पर))",
                r"(?:उल्लंघन|चूक|विफलता)",
            ], "label": "समाप्ति के कारण निर्दिष्ट"},
        ],
        "weight_factor": 0.6,
    },
    "liability": {
        "checks": [
            {"name": "cap_defined", "patterns": [
                r"(?:सीमा|अधिकतम)\s+(?:दायित्व|जिम्मेदारी)",
                r"(?:दायित्व|जिम्मेदारी)\s+(?:से\s+अधिक\s+नहीं|सीमित)",
            ], "label": "दायित्व सीमा परिभाषित"},
        ],
        "weight_factor": 0.5,
    },
    "confidentiality": {
        "checks": [
            {"name": "duration", "patterns": [
                r"(?:गोपनीयता\s+)?(?:अवधि|अवधि\s+के\s+लिए)",
                r"\d+\s*(?:वर्ष|महीने|साल)\s+(?:तक|के\s+लिए)",
            ], "label": "गोपनीयता अवधि परिभाषित"},
        ],
        "weight_factor": 0.4,
    },
}


def check_compliance(
    clauses: List[Dict],
    full_text: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Check document compliance against essential clause checklist.
    Now includes structural quality validation beyond just presence.

    Returns:
        Dict with:
        - compliance_score: 0-100
        - found_clauses: list of detected essential clauses
        - missing_clauses: list of missing essential clauses
        - details: per-clause compliance info (with quality assessment)
    """
    checklist = HINDI_ESSENTIAL_CLAUSES if language == "hi" else ESSENTIAL_CLAUSES
    validators = HINDI_STRUCTURAL_VALIDATORS if language == "hi" else STRUCTURAL_VALIDATORS
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

        # ── Structural quality validation ──
        quality_score = 1.0  # Default: full quality if present
        quality_details = []

        if is_found and clause_name in validators:
            quality_score, quality_details = _validate_clause_quality(
                text_lower, validators[clause_name]
            )

        detail = {
            "clause_type": clause_name,
            "description": config["description"],
            "weight": config["weight"],
            "found": is_found,
            "matched_keyword": matched_keyword,
            "quality_score": round(quality_score, 2),
            "quality_checks": quality_details,
        }

        if is_found:
            found.append(clause_name)
            # Score = weight × quality (presence × quality)
            earned_weight += config["weight"] * quality_score
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


def _validate_clause_quality(
    text_lower: str,
    validator: Dict
) -> Tuple[float, List[Dict]]:
    """
    Validate clause quality by checking structural elements.
    Returns (quality_score 0-1, details of checks).
    """
    checks = validator["checks"]
    weight_factor = validator.get("weight_factor", 0.5)

    passed = 0
    total = len(checks)
    check_results = []

    for check in checks:
        found = False
        for pattern in check["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                found = True
                break

        check_results.append({
            "name": check["name"],
            "label": check["label"],
            "passed": found,
        })

        if found:
            passed += 1

    # Quality score: interpolate between weight_factor and 1.0
    # If all checks pass: quality = 1.0
    # If no checks pass: quality = weight_factor (still gets some credit for presence)
    if total > 0:
        quality = weight_factor + (1 - weight_factor) * (passed / total)
    else:
        quality = 1.0

    return quality, check_results


def _weight_to_importance(weight: int) -> str:
    """Convert weight to importance label."""
    if weight >= 9:
        return "critical"
    elif weight >= 7:
        return "important"
    else:
        return "recommended"
