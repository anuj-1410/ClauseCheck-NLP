"""
ClauseCheck – Risk Detection Service
Detects risky clauses in legal documents using pattern matching
AND semantic similarity analysis via multilingual sentence-transformers.

Upgrades:
  - Added semantic similarity using paraphrase-multilingual-mpnet-base-v2
  - Cross-lingual risk detection: Hindi clause ↔ English prototypes
  - Regex patterns kept as primary; semantic layer is additive
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Lazy-loaded semantic model
_semantic_model = None

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

# ──────────────────────────────────────────────
# Semantic risk prototypes (English) for cross-lingual matching
# ──────────────────────────────────────────────
RISK_PROTOTYPES = {
    "unlimited_liability": [
        "Unlimited liability without any cap.",
        "The consultant shall bear responsibility without limitation.",
        "No limit on damages or liability.",
        "Full and complete liability for all losses.",
    ],
    "one_sided_termination": [
        "One party can terminate the agreement at any time without reason.",
        "Unilateral termination without notice.",
        "The company has exclusive right to end this contract.",
    ],
    "non_compete_broad": [
        "The employee shall not compete or work for any competitor.",
        "Broad non-compete restriction preventing all competitive activity.",
        "Prohibition from engaging in any similar business.",
    ],
    "waiver_of_rights": [
        "The party irrevocably waives all legal rights and claims.",
        "Complete waiver of rights to sue or seek damages.",
        "Giving up all rights to compensation.",
    ],
    "indemnification_broad": [
        "Indemnify against all claims, losses, damages and liabilities.",
        "Full indemnification for any and all losses.",
        "Hold harmless from all third-party claims.",
    ],
    "auto_renewal": [
        "The contract automatically renews unless cancelled.",
        "Deemed renewed without notice for additional terms.",
    ],
    "confidentiality_perpetual": [
        "Confidentiality obligations continue indefinitely without time limit.",
        "Perpetual confidentiality with no expiration.",
    ],
}

SEMANTIC_THRESHOLD = 0.65  # Cosine similarity threshold


def _get_semantic_model():
    """Lazy-load sentence-transformer model for semantic similarity."""
    global _semantic_model
    if _semantic_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _semantic_model = SentenceTransformer(
                "paraphrase-multilingual-mpnet-base-v2"
            )
            logger.info("Semantic risk model (multilingual mpnet) loaded.")
        except Exception as e:
            logger.warning(f"Failed to load semantic model: {e}. Semantic risk detection disabled.")
            _semantic_model = False  # Mark as failed, don't retry
    return _semantic_model if _semantic_model is not False else None


def detect_risks(
    clauses: List[Dict],
    language: str = "en"
) -> List[Dict[str, Any]]:
    """
    Detect risky clauses in the document using regex + semantic similarity.

    Returns:
        List of risk findings with:
        - clause_id: which clause
        - clause_text: the clause text
        - risk_type: category of risk
        - severity: 'high', 'medium', or 'low'
        - description: human-readable explanation
        - matched_text: the specific text that triggered the risk
        - risk_score: numeric score (1-10)
        - detection_method: 'pattern' or 'semantic'
    """
    risks = []
    patterns = HINDI_RISK_PATTERNS if language == "hi" else RISK_PATTERNS

    # Track which clauses already have which risk types (to avoid duplicates)
    found_risks = set()  # (clause_id, risk_type)

    # ── Layer 1: Regex pattern matching ──
    for clause in clauses:
        clause_risks = _analyze_clause_risk(clause, patterns)
        for r in clause_risks:
            r["detection_method"] = "pattern"
            found_risks.add((r["clause_id"], r["risk_type"]))
        risks.extend(clause_risks)

    # ── Layer 2: Semantic similarity (cross-lingual) ──
    semantic_risks = _detect_semantic_risks(clauses, found_risks)
    risks.extend(semantic_risks)

    logger.info(f"Detected {len(risks)} risk findings ({len(semantic_risks)} semantic).")
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
                    "risk_score": score,
                    "detection_method": "pattern",
                })
                break  # One finding per risk type per clause

    return findings


def _detect_semantic_risks(
    clauses: List[Dict],
    already_found: set
) -> List[Dict[str, Any]]:
    """
    Detect risks using semantic similarity against risk prototypes.
    Works cross-lingually: Hindi clauses match English prototypes.
    """
    model = _get_semantic_model()
    if model is None:
        return []

    findings = []

    try:
        import numpy as np

        # Pre-encode all risk prototypes
        proto_embeddings = {}
        for risk_type, prototypes in RISK_PROTOTYPES.items():
            proto_embeddings[risk_type] = model.encode(prototypes, convert_to_numpy=True)

        # Encode all clause texts
        clause_texts = [c["text"][:500] for c in clauses]
        if not clause_texts:
            return []

        clause_embeddings = model.encode(clause_texts, convert_to_numpy=True)

        # Compare each clause against each risk prototype set
        for i, clause in enumerate(clauses):
            clause_emb = clause_embeddings[i].reshape(1, -1)

            for risk_type, proto_embs in proto_embeddings.items():
                # Skip if this clause-risk combo was already found by regex
                if (clause["id"], risk_type) in already_found:
                    continue

                # Compute cosine similarity with each prototype
                similarities = np.dot(proto_embs, clause_emb.T).flatten()
                # Normalize
                norms_proto = np.linalg.norm(proto_embs, axis=1)
                norm_clause = np.linalg.norm(clause_emb)
                if norm_clause > 0:
                    similarities = similarities / (norms_proto * norm_clause)

                max_sim = float(np.max(similarities))

                if max_sim >= SEMANTIC_THRESHOLD:
                    severity_map = {
                        "unlimited_liability": "high",
                        "one_sided_termination": "high",
                        "waiver_of_rights": "high",
                        "indemnification_broad": "high",
                        "non_compete_broad": "medium",
                        "auto_renewal": "medium",
                        "confidentiality_perpetual": "medium",
                    }
                    severity = severity_map.get(risk_type, "medium")
                    score = {"high": 7, "medium": 4, "low": 2}[severity]

                    findings.append({
                        "clause_id": clause["id"],
                        "clause_text": clause["text"][:300],
                        "risk_type": risk_type,
                        "severity": severity,
                        "description": RISK_PATTERNS.get(risk_type, {}).get(
                            "description",
                            f"Semantic match for {risk_type.replace('_', ' ')}"
                        ),
                        "matched_text": f"[semantic match: {max_sim:.2f}]",
                        "risk_score": score,
                        "detection_method": "semantic",
                    })
                    already_found.add((clause["id"], risk_type))

    except Exception as e:
        logger.warning(f"Semantic risk detection failed: {e}")

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
