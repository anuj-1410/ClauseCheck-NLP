"""
ClauseCheck – Obligation Detection Service
Detects contractual obligations by identifying modal verbs,
responsible parties, actions, conditions, and deadlines.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Obligation indicators
# ──────────────────────────────────────────────
MANDATORY_MODALS = {"shall", "must", "is required to", "is obligated to", "will"}
RECOMMENDED_MODALS = {"should", "ought to", "is expected to", "is advised to"}
OPTIONAL_MODALS = {"may", "can", "is permitted to", "is entitled to", "has the right to"}

HINDI_MANDATORY = {"करेगा", "करेगी", "करेंगे", "होगा", "होगी", "अवश्य", "आवश्यक"}
HINDI_OPTIONAL = {"सकता", "सकती", "सकते", "कर सकता", "अनुमति"}

# Deadline patterns
DEADLINE_PATTERNS = [
    r"within\s+(\d+\s*(?:days?|weeks?|months?|years?|business\s+days?))",
    r"no\s+later\s+than\s+(.+?)(?:\.|,|;|$)",
    r"by\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    r"before\s+(.+?)(?:\.|,|;|$)",
    r"on\s+or\s+before\s+(.+?)(?:\.|,|;|$)",
]

# Condition patterns
CONDITION_PATTERNS = [
    r"(?:provided\s+that|subject\s+to|in\s+the\s+event\s+(?:that|of)|"
    r"if\s+and\s+only\s+if|upon|in\s+case\s+of|where)\s+(.+?)(?:\.|,|;|$)",
]


def detect_obligations(
    clauses: List[Dict],
    language: str = "en"
) -> List[Dict[str, Any]]:
    """
    Detect obligations in segmented clauses.

    Returns:
        List of obligation dicts with:
        - clause_id: which clause this belongs to
        - text: the obligation text
        - strength: 'mandatory', 'recommended', or 'optional'
        - modal: the triggering word/phrase
        - party: responsible party (if detected)
        - action: the required action
        - deadline: any deadline mentioned
        - condition: any conditions mentioned
    """
    obligations = []

    for clause in clauses:
        clause_text = clause["text"]
        clause_obligations = _analyze_clause(clause_text, clause["id"], language)
        obligations.extend(clause_obligations)

    logger.info(f"Detected {len(obligations)} obligations.")
    return obligations


def _analyze_clause(
    text: str,
    clause_id: int,
    language: str
) -> List[Dict[str, Any]]:
    """Analyze a single clause for obligations."""
    obligations = []
    text_lower = text.lower()

    if language == "hi":
        obligations.extend(_detect_hindi_obligations(text, clause_id))
    else:
        obligations.extend(_detect_english_obligations(text, text_lower, clause_id))

    return obligations


def _detect_english_obligations(
    text: str,
    text_lower: str,
    clause_id: int
) -> List[Dict[str, Any]]:
    """Detect obligations in English text."""
    obligations = []

    # Check each sentence for modals
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        sent_lower = sentence.lower().strip()
        if not sent_lower:
            continue

        # Check mandatory modals
        for modal in MANDATORY_MODALS:
            if modal in sent_lower:
                obligation = _build_obligation(
                    sentence, clause_id, modal, "mandatory"
                )
                obligations.append(obligation)
                break
        else:
            # Check recommended modals
            for modal in RECOMMENDED_MODALS:
                if modal in sent_lower:
                    obligation = _build_obligation(
                        sentence, clause_id, modal, "recommended"
                    )
                    obligations.append(obligation)
                    break
            else:
                # Check optional modals
                for modal in OPTIONAL_MODALS:
                    if modal in sent_lower:
                        obligation = _build_obligation(
                            sentence, clause_id, modal, "optional"
                        )
                        obligations.append(obligation)
                        break

    return obligations


def _detect_hindi_obligations(
    text: str,
    clause_id: int
) -> List[Dict[str, Any]]:
    """Detect obligations in Hindi text."""
    obligations = []

    sentences = re.split(r'(?<=[।])\s*', text)

    for sentence in sentences:
        if not sentence.strip():
            continue

        for modal in HINDI_MANDATORY:
            if modal in sentence:
                obligations.append({
                    "clause_id": clause_id,
                    "text": sentence.strip(),
                    "strength": "mandatory",
                    "modal": modal,
                    "party": "",
                    "action": sentence.strip(),
                    "deadline": "",
                    "condition": ""
                })
                break
        else:
            for modal in HINDI_OPTIONAL:
                if modal in sentence:
                    obligations.append({
                        "clause_id": clause_id,
                        "text": sentence.strip(),
                        "strength": "optional",
                        "modal": modal,
                        "party": "",
                        "action": sentence.strip(),
                        "deadline": "",
                        "condition": ""
                    })
                    break

    return obligations


def _build_obligation(
    sentence: str,
    clause_id: int,
    modal: str,
    strength: str
) -> Dict[str, Any]:
    """Build an obligation dict from a sentence with a detected modal."""
    sent_lower = sentence.lower()

    # Extract party (subject before the modal verb)
    party = ""
    modal_idx = sent_lower.find(modal)
    if modal_idx > 0:
        subject_text = sentence[:modal_idx].strip()
        # Take last few words as the party name
        words = subject_text.split()
        if words:
            party = " ".join(words[-3:]).strip(" ,;:")

    # Extract action (text after the modal)
    action = ""
    if modal_idx >= 0:
        action = sentence[modal_idx + len(modal):].strip(" ,;:.")

    # Extract deadline
    deadline = ""
    for pattern in DEADLINE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            deadline = match.group(1).strip()
            break

    # Extract condition
    condition = ""
    for pattern in CONDITION_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            condition = match.group(1).strip()
            break

    return {
        "clause_id": clause_id,
        "text": sentence.strip(),
        "strength": strength,
        "modal": modal,
        "party": party,
        "action": action[:200],  # Truncate long actions
        "deadline": deadline,
        "condition": condition[:200]
    }
