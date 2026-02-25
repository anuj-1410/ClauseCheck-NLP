"""
ClauseCheck – Risk Detection Service
Detects risky clauses in legal documents using pattern matching
and semantic similarity analysis.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Risk patterns with categories and severity
# ──────────────────────────────────────────────
RISK_PATTERNS = {
    "unlimited_liability": {
        "patterns": [
            r"unlimited\s+liability",
            r"liable\s+for\s+all\s+(?:damages|losses)",
            r"no\s+(?:cap|limit|limitation)\s+(?:on|to)\s+(?:liability|damages)",
            r"full\s+(?:and\s+complete\s+)?liability",
            r"indemnify\s+(?:and\s+hold\s+harmless\s+)?(?:against\s+)?all",
            r"without\s+(?:any\s+)?limit(?:ation)?",
        ],
        "severity": "high",
        "description": "Unlimited or uncapped liability clause detected"
    },
    "one_sided_termination": {
        "patterns": [
            r"(?:may|can|shall)\s+terminate\s+(?:this\s+)?(?:agreement|contract)\s+(?:at\s+)?(?:any\s+time|without\s+(?:cause|reason|notice))",
            r"sole\s+(?:and\s+absolute\s+)?discretion\s+to\s+terminate",
            r"unilateral(?:ly)?\s+terminat",
            r"terminate\s+without\s+(?:prior\s+)?(?:notice|cause|reason)",
            r"right\s+to\s+terminate\s+(?:at\s+will|immediately)",
        ],
        "severity": "high",
        "description": "One-sided or at-will termination clause detected"
    },
    "missing_notice_period": {
        "patterns": [
            r"terminat\w+\s+(?:without|with\s+no)\s+(?:prior\s+)?notice",
            r"immediate(?:ly)?\s+terminat",
            r"no\s+(?:prior\s+)?notice\s+(?:is\s+)?required",
            r"without\s+(?:any\s+)?advance\s+notice",
        ],
        "severity": "high",
        "description": "Missing or waived notice period for termination"
    },
    "auto_renewal": {
        "patterns": [
            r"auto(?:matic(?:ally)?)?[\s-]+renew",
            r"shall\s+(?:automatically\s+)?(?:be\s+)?renewed?\s+(?:for|unless)",
            r"deemed\s+(?:to\s+be\s+)?renewed",
            r"renew(?:ed|al)\s+(?:automatically|without\s+notice)",
        ],
        "severity": "medium",
        "description": "Auto-renewal clause detected"
    },
    "vague_penalties": {
        "patterns": [
            r"(?:reasonable|appropriate|adequate|suitable)\s+(?:penalty|penalt|damages|compensation)",
            r"(?:penalty|penalties)\s+(?:as\s+)?(?:deemed|determined)\s+(?:fit|appropriate|necessary)",
            r"(?:liquidated\s+)?damages\s+(?:to\s+be\s+)?determined",
            r"penalty\s+(?:amount\s+)?(?:not|to\s+be)\s+(?:specified|determined\s+later)",
        ],
        "severity": "medium",
        "description": "Vague or undefined penalty clause"
    },
    "non_compete_broad": {
        "patterns": [
            r"non[\s-]?compete?\s+(?:clause|agreement|covenant|restriction)",
            r"(?:shall|will)\s+not\s+(?:directly\s+or\s+indirectly\s+)?(?:engage|compete|work|participate)",
            r"refrain\s+from\s+(?:any\s+)?(?:competitive|competing)\s+activit",
            r"restrictive\s+covenant",
        ],
        "severity": "medium",
        "description": "Broad non-compete clause detected"
    },
    "waiver_of_rights": {
        "patterns": [
            r"waive(?:s|r)?\s+(?:all|any|the\s+right\s+to)",
            r"irrevocabl[ey]\s+waive",
            r"forever\s+(?:waive|relinquish|abandon)",
            r"give\s+up\s+(?:all|any)\s+(?:rights?|claims?)",
        ],
        "severity": "high",
        "description": "Waiver of significant rights detected"
    },
    "exclusive_jurisdiction": {
        "patterns": [
            r"exclusive\s+jurisdiction\s+of\s+(?:the\s+)?courts?\s+(?:of|in|at)",
            r"submit\s+to\s+(?:the\s+)?(?:exclusive\s+)?jurisdiction",
            r"(?:sole|exclusive)\s+venue",
        ],
        "severity": "low",
        "description": "Exclusive jurisdiction clause – may limit legal options"
    },
    "indemnification_broad": {
        "patterns": [
            r"indemnif(?:y|ies|ication)\s+(?:and\s+hold\s+harmless\s+)?(?:against\s+)?(?:all|any|every)",
            r"(?:full|complete|total)\s+indemnif(?:y|ication)",
            r"indemnif\w+\s+(?:from\s+and\s+against\s+)?(?:any\s+and\s+)?all\s+(?:claims|losses|damages|liabilities)",
        ],
        "severity": "high",
        "description": "Broad indemnification obligation detected"
    },
    "confidentiality_perpetual": {
        "patterns": [
            r"confidential(?:ity)?\s+(?:obligations?\s+)?(?:shall\s+)?(?:survive|remain|continue)\s+(?:in\s+perpetuity|indefinitely|forever)",
            r"perpetual\s+confidential(?:ity)?",
            r"no\s+(?:time\s+)?limit\s+(?:on\s+)?confidential(?:ity)?",
        ],
        "severity": "medium",
        "description": "Perpetual or indefinite confidentiality obligation"
    },
}

# Hindi risk patterns
HINDI_RISK_PATTERNS = {
    "unlimited_liability": {
        "patterns": [
            r"असीमित\s+(?:दायित्व|जिम्मेदारी)",
            r"पूर्ण\s+(?:दायित्व|जिम्मेदारी)",
            r"बिना\s+(?:किसी\s+)?सीमा",
        ],
        "severity": "high",
        "description": "असीमित दायित्व का खंड पाया गया"
    },
    "one_sided_termination": {
        "patterns": [
            r"(?:एकतरफा|एकपक्षीय)\s+(?:समाप्ति|रद्द)",
            r"बिना\s+(?:कारण|सूचना)\s+(?:समाप्त|रद्द)",
        ],
        "severity": "high",
        "description": "एकतरफा समाप्ति का खंड पाया गया"
    },
}


def detect_risks(
    clauses: List[Dict],
    language: str = "en"
) -> List[Dict[str, Any]]:
    """
    Detect risky clauses in the document.

    Returns:
        List of risk findings with:
        - clause_id: which clause
        - clause_text: the clause text
        - risk_type: category of risk
        - severity: 'high', 'medium', or 'low'
        - description: human-readable explanation
        - matched_text: the specific text that triggered the risk
        - risk_score: numeric score (1-10)
    """
    risks = []
    patterns = HINDI_RISK_PATTERNS if language == "hi" else RISK_PATTERNS

    for clause in clauses:
        clause_risks = _analyze_clause_risk(clause, patterns)
        risks.extend(clause_risks)

    logger.info(f"Detected {len(risks)} risk findings.")
    return risks


def _analyze_clause_risk(
    clause: Dict,
    patterns: Dict
) -> List[Dict[str, Any]]:
    """Analyze a single clause for risk patterns."""
    findings = []
    text = clause["text"]
    text_lower = text.lower()

    for risk_type, config in patterns.items():
        for pattern in config["patterns"]:
            match = re.search(pattern, text_lower)
            if match:
                severity = config["severity"]
                score = {"high": 8, "medium": 5, "low": 2}[severity]

                findings.append({
                    "clause_id": clause["id"],
                    "clause_text": text[:300],
                    "risk_type": risk_type,
                    "severity": severity,
                    "description": config["description"],
                    "matched_text": match.group(),
                    "risk_score": score
                })
                break  # One finding per risk type per clause

    return findings


def calculate_overall_risk_score(risks: List[Dict]) -> int:
    """
    Calculate an overall document risk score (0–100).

    Higher score = more risk.
    """
    if not risks:
        return 5  # Minimal risk if nothing detected

    total_score = sum(r["risk_score"] for r in risks)
    max_possible = len(risks) * 10

    # Normalize to 0-100
    raw_score = (total_score / max_possible) * 100 if max_possible > 0 else 0

    # Boost if many high-severity findings
    high_count = sum(1 for r in risks if r["severity"] == "high")
    boost = min(high_count * 5, 25)

    final_score = min(int(raw_score + boost), 100)
    return max(final_score, 5)  # At least 5 if any risks found
