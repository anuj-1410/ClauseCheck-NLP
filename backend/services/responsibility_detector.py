"""
ClauseCheck – Responsibility & Ambiguity Detector
Detects passive voice, vague terms, missing subjects,
and ambiguous obligations in legal clauses.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Vague / ambiguous terms commonly hidden in contracts
# ──────────────────────────────────────────────
VAGUE_TERMS = {
    "en": [
        "reasonable", "reasonably", "promptly", "adequate", "adequately",
        "appropriate", "appropriately", "timely", "as soon as practicable",
        "best efforts", "good faith", "commercially reasonable",
        "material", "materially", "substantial", "substantially",
        "satisfactory", "sufficient", "sufficiently", "fair", "fairly",
        "customary", "usual", "normal", "proper", "properly",
        "from time to time", "as necessary", "as applicable",
        "to the extent possible", "in its sole discretion",
        "without limitation", "including but not limited to",
    ],
    "hi": [
        "उचित", "यथोचित", "शीघ्र", "पर्याप्त", "उपयुक्त",
        "समयानुसार", "संतोषजनक", "आवश्यक", "सामान्य",
        "यथासंभव", "अपने विवेक से",
    ],
}

# Passive voice patterns (English)
PASSIVE_PATTERNS = [
    r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+\s+)?(?:required|obligated|expected|"
    r"permitted|authorized|entitled|deemed|considered|ensured|maintained|provided|"
    r"delivered|completed|performed|executed|fulfilled|determined|decided|"
    r"agreed|approved|accepted|rejected|terminated|renewed|amended|modified)\b",
    r"\b(?:shall|will|must|should|may)\s+be\s+\w+ed\b",
    r"\b(?:it\s+is|it\s+shall\s+be)\s+(?:the\s+)?(?:responsibility|duty|obligation)\b",
]

# Patterns indicating missing/unclear responsible party
MISSING_SUBJECT_PATTERNS = [
    r"^\s*(?:shall|must|will|should)\s+(?:be\s+)?(?:\w+ed)\b",
    r"\b(?:the\s+(?:same|said|aforesaid))\s+shall\b",
    r"\b(?:it|this)\s+(?:shall|must|will)\b",
]


def detect_responsibility_issues(
    clauses: List[Dict],
    language: str = "en"
) -> Dict[str, Any]:
    """
    Analyze clauses for responsibility and ambiguity issues.

    Returns:
        Dict with:
        - passive_voice: list of passive voice findings
        - vague_terms: list of vague term findings
        - missing_subjects: list of unclear responsibility findings
        - ambiguity_score: overall ambiguity score (0-100)
        - total_issues: total count of all issues
    """
    passive_voice = []
    vague_terms_found = []
    missing_subjects = []

    lang = language if language in ("en", "hi") else "en"
    vague_list = VAGUE_TERMS.get(lang, VAGUE_TERMS["en"])

    for clause in clauses:
        text = clause["text"]
        clause_id = clause["id"]

        # Detect passive voice
        if lang == "en":
            for pattern in PASSIVE_PATTERNS:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for m in matches:
                    passive_voice.append({
                        "clause_id": clause_id,
                        "matched_text": m.group(),
                        "full_text": text[:200],
                        "issue": "Passive voice — unclear who is responsible",
                        "suggestion": "Rewrite in active voice specifying the responsible party.",
                        "confidence": 0.85,
                    })

            # Detect missing subjects
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sent in sentences:
                for pattern in MISSING_SUBJECT_PATTERNS:
                    if re.search(pattern, sent.strip(), re.IGNORECASE):
                        missing_subjects.append({
                            "clause_id": clause_id,
                            "matched_text": sent.strip()[:150],
                            "issue": "Unclear responsible party — who must perform this action?",
                            "confidence": 0.75,
                        })
                        break

        # Detect vague terms
        text_lower = text.lower()
        for term in vague_list:
            if term.lower() in text_lower:
                idx = text_lower.find(term.lower())
                context_start = max(0, idx - 30)
                context_end = min(len(text), idx + len(term) + 30)
                context = text[context_start:context_end]

                vague_terms_found.append({
                    "clause_id": clause_id,
                    "term": term,
                    "context": f"...{context}...",
                    "issue": f'Vague term "{term}" — lacks precise definition',
                    "suggestion": f'Define what "{term}" specifically means in this context.',
                    "confidence": 0.80,
                })

    # Deduplicate vague terms per clause
    seen = set()
    deduped_vague = []
    for v in vague_terms_found:
        key = (v["clause_id"], v["term"])
        if key not in seen:
            seen.add(key)
            deduped_vague.append(v)
    vague_terms_found = deduped_vague

    total = len(passive_voice) + len(vague_terms_found) + len(missing_subjects)

    # Calculate ambiguity score (0-100) — higher = more ambiguous
    clause_count = max(len(clauses), 1)
    raw = (total / clause_count) * 25
    ambiguity_score = min(int(raw), 100)

    logger.info(
        f"Responsibility analysis: {len(passive_voice)} passive voice, "
        f"{len(vague_terms_found)} vague terms, {len(missing_subjects)} missing subjects"
    )

    return {
        "passive_voice": passive_voice,
        "vague_terms": vague_terms_found,
        "missing_subjects": missing_subjects,
        "ambiguity_score": ambiguity_score,
        "total_issues": total,
    }
