"""
ClauseCheck – Obligation Detection Service
Detects contractual obligations by identifying modal verbs,
responsible parties, actions, conditions, and deadlines.

Upgrades:
  - English: spaCy dependency parsing (nsubj, ROOT, dobj) for structured obligations
  - Hindi: Stanza dependency parsing with passive form detection
  - Power imbalance & one-sided vs mutual obligation detection
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global NLP model references (loaded lazily)
_spacy_nlp = None
_stanza_dep_nlp = None

# ──────────────────────────────────────────────
# Obligation indicators
# ──────────────────────────────────────────────
MANDATORY_MODALS = {"shall", "must", "is required to", "is obligated to", "will"}
RECOMMENDED_MODALS = {"should", "ought to", "is expected to", "is advised to"}
OPTIONAL_MODALS = {"may", "can", "is permitted to", "is entitled to", "has the right to"}

HINDI_MANDATORY = {"करेगा", "करेगी", "करेंगे", "होगा", "होगी", "अवश्य", "आवश्यक"}
HINDI_OPTIONAL = {"सकता", "सकती", "सकते", "कर सकता", "अनुमति"}

# Hindi passive forms
HINDI_PASSIVE_FORMS = {"किया जाएगा", "किया गया", "किया जाना चाहिए", "की जाएगी", "किए जाएंगे"}

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


def _get_spacy():
    """Lazy-load spaCy English model for dependency parsing."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_trf")
                logger.info("spaCy en_core_web_trf loaded for obligation detection.")
            except OSError:
                _spacy_nlp = spacy.load("en_core_web_sm")
                logger.info("Using en_core_web_sm fallback for obligation detection.")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            return None
    return _spacy_nlp


def _get_stanza_dep():
    """Lazy-load Stanza Hindi model with dependency parsing."""
    global _stanza_dep_nlp
    if _stanza_dep_nlp is None:
        try:
            import stanza
            _stanza_dep_nlp = stanza.Pipeline(
                "hi", processors="tokenize,pos,lemma,depparse", verbose=False
            )
            logger.info("Stanza Hindi dependency parser loaded.")
        except Exception as e:
            logger.error(f"Failed to load Stanza dep parser: {e}")
            return None
    return _stanza_dep_nlp


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
        - obligation_type: 'unilateral' or 'mutual'
        - is_passive: whether the obligation uses passive voice
    """
    obligations = []

    for clause in clauses:
        clause_text = clause["text"]
        clause_obligations = _analyze_clause(clause_text, clause["id"], language)
        obligations.extend(clause_obligations)

    # Detect power imbalance
    obligations = _detect_power_imbalance(obligations)

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
    """Detect obligations in English text using dependency parsing."""
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
                obligation = _build_obligation_with_deps(
                    sentence, clause_id, modal, "mandatory"
                )
                obligations.append(obligation)
                break
        else:
            # Check recommended modals
            for modal in RECOMMENDED_MODALS:
                if modal in sent_lower:
                    obligation = _build_obligation_with_deps(
                        sentence, clause_id, modal, "recommended"
                    )
                    obligations.append(obligation)
                    break
            else:
                # Check optional modals
                for modal in OPTIONAL_MODALS:
                    if modal in sent_lower:
                        obligation = _build_obligation_with_deps(
                            sentence, clause_id, modal, "optional"
                        )
                        obligations.append(obligation)
                        break

    return obligations


def _build_obligation_with_deps(
    sentence: str,
    clause_id: int,
    modal: str,
    strength: str
) -> Dict[str, Any]:
    """Build obligation using spaCy dependency parsing for subject/verb/object extraction."""
    sent_lower = sentence.lower()

    # Defaults from simple text processing
    party = ""
    action = ""
    is_passive = False

    # ── Dependency parsing with spaCy ──
    nlp = _get_spacy()
    if nlp is not None:
        try:
            doc = nlp(sentence[:500])  # Limit length
            subjects = []
            root_verb = ""
            objects = []

            for token in doc:
                # Extract subject (nsubj or nsubjpass)
                if token.dep_ in ("nsubj", "nsubjpass"):
                    # Get the full subtree for proper noun phrases
                    subject_span = " ".join(
                        [t.text for t in token.subtree
                         if t.dep_ not in ("punct", "cc", "conj")]
                    )
                    subjects.append(subject_span)
                    if token.dep_ == "nsubjpass":
                        is_passive = True

                # Extract ROOT verb
                if token.dep_ == "ROOT":
                    root_verb = token.text

                # Extract direct object
                if token.dep_ in ("dobj", "attr", "oprd"):
                    obj_span = " ".join(
                        [t.text for t in token.subtree
                         if t.dep_ not in ("punct",)]
                    )
                    objects.append(obj_span)

            if subjects:
                party = subjects[0].strip(" ,;:")
            if root_verb:
                action = root_verb
                if objects:
                    action = f"{root_verb} {'; '.join(objects)}"

        except Exception as e:
            logger.debug(f"Dependency parsing failed for obligation: {e}")

    # Fallback: simple text extraction if dep parse didn't yield results
    if not party:
        modal_idx = sent_lower.find(modal)
        if modal_idx > 0:
            subject_text = sentence[:modal_idx].strip()
            words = subject_text.split()
            if words:
                party = " ".join(words[-3:]).strip(" ,;:")

    if not action:
        modal_idx = sent_lower.find(modal)
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
        "action": action[:200],
        "deadline": deadline,
        "condition": condition[:200],
        "obligation_type": "unilateral",  # Will be refined by _detect_power_imbalance
        "is_passive": is_passive,
    }


def _detect_hindi_obligations(
    text: str,
    clause_id: int
) -> List[Dict[str, Any]]:
    """Detect obligations in Hindi text using Stanza dependency parsing."""
    obligations = []

    sentences = re.split(r'(?<=[।])\s*', text)

    for sentence in sentences:
        if not sentence.strip():
            continue

        is_passive = False
        party = ""
        action = sentence.strip()

        # Check for passive forms
        for passive_form in HINDI_PASSIVE_FORMS:
            if passive_form in sentence:
                is_passive = True
                break

        # ── Stanza dependency parsing for Hindi ──
        stanza_nlp = _get_stanza_dep()
        if stanza_nlp is not None:
            try:
                doc = stanza_nlp(sentence[:500])
                for sent in doc.sentences:
                    for word in sent.words:
                        if word.deprel in ("nsubj", "nsubj:pass"):
                            party = word.text
                            if word.deprel == "nsubj:pass":
                                is_passive = True
                        if word.deprel == "root":
                            action = word.text
            except Exception as e:
                logger.debug(f"Hindi dep parsing failed: {e}")

        for modal in HINDI_MANDATORY:
            if modal in sentence:
                obligations.append({
                    "clause_id": clause_id,
                    "text": sentence.strip(),
                    "strength": "mandatory",
                    "modal": modal,
                    "party": party,
                    "action": action,
                    "deadline": "",
                    "condition": "",
                    "obligation_type": "unilateral",
                    "is_passive": is_passive,
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
                        "party": party,
                        "action": action,
                        "deadline": "",
                        "condition": "",
                        "obligation_type": "unilateral",
                        "is_passive": is_passive,
                    })
                    break

    return obligations


def _detect_power_imbalance(obligations: List[Dict]) -> List[Dict]:
    """
    Analyze obligation distribution to detect power imbalance.
    If one party has significantly more mandatory obligations, flag it.
    Also classify obligations as mutual vs unilateral.
    """
    # Count obligations per party
    party_counts = {}
    for ob in obligations:
        p = ob.get("party", "").strip().lower()
        if p:
            party_counts[p] = party_counts.get(p, 0) + 1

    # If only one party has obligations → all are unilateral
    # If both parties have obligations → classify
    parties = list(party_counts.keys())

    if len(parties) >= 2:
        # Sort by obligation count
        sorted_parties = sorted(party_counts.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_parties[0][0]
        dominant_count = sorted_parties[0][1]
        total = sum(c for _, c in sorted_parties)

        for ob in obligations:
            p = ob.get("party", "").strip().lower()
            if p == dominant and dominant_count / total > 0.7:
                ob["obligation_type"] = "unilateral"
            elif p:
                ob["obligation_type"] = "mutual"

    return obligations
