"""
ClauseCheck – Responsibility & Ambiguity Detector
Detects passive voice, vague terms, missing subjects,
and ambiguous obligations in legal clauses.

Upgrades:
  - English: spaCy dependency parsing (nsubjpass) instead of regex for passive voice
  - Hindi: Stanza dependency labels + passive construction patterns
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Global NLP model references
_spacy_nlp = None
_stanza_nlp = None

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

# Hindi passive construction patterns (used alongside Stanza dep labels)
HINDI_PASSIVE_PATTERNS = [
    r"\bगया\b", r"\bगई\b", r"\bगए\b",
    r"\bकी गई\b", r"\bकिया गया\b",
    r"\bकिया जाएगा\b", r"\bकी जाएगी\b", r"\bकिए जाएंगे\b",
    r"\bकिया जाना चाहिए\b",
    r"\bदिया जाएगा\b", r"\bदी जाएगी\b",
]

# Passive voice regex fallback patterns (English) — used if spaCy unavailable
PASSIVE_PATTERNS_FALLBACK = [
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


def _get_spacy():
    """Lazy-load spaCy model for dependency-based passive detection."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_trf")
            except OSError:
                _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded for responsibility detection.")
        except Exception as e:
            logger.error(f"Failed to load spaCy: {e}")
            _spacy_nlp = False  # Mark as failed
    return _spacy_nlp if _spacy_nlp is not False else None


def _get_stanza():
    """Lazy-load Stanza Hindi model with dependency parsing."""
    global _stanza_nlp
    if _stanza_nlp is None:
        try:
            import stanza
            _stanza_nlp = stanza.Pipeline(
                "hi", processors="tokenize,pos,lemma,depparse", verbose=False
            )
            logger.info("Stanza Hindi dep parser loaded for responsibility detection.")
        except Exception as e:
            logger.error(f"Failed to load Stanza: {e}")
            _stanza_nlp = False
    return _stanza_nlp if _stanza_nlp is not False else None


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
            passive_findings = _detect_passive_english(text, clause_id)
            passive_voice.extend(passive_findings)

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
        elif lang == "hi":
            passive_findings = _detect_passive_hindi(text, clause_id)
            passive_voice.extend(passive_findings)

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


def _detect_passive_english(text: str, clause_id: int) -> List[Dict]:
    """
    Detect passive voice in English using spaCy dependency parsing (nsubjpass).
    Falls back to regex if spaCy is unavailable.
    """
    findings = []
    nlp = _get_spacy()

    if nlp is not None:
        try:
            doc = nlp(text[:5000])
            seen_spans = set()

            for token in doc:
                if token.dep_ == "nsubjpass":
                    # Get the sentence containing this passive subject
                    sent = token.sent
                    sent_text = sent.text.strip()

                    if sent_text in seen_spans:
                        continue
                    seen_spans.add(sent_text)

                    # Get the passive verb (head of nsubjpass)
                    passive_verb = token.head.text
                    matched = f"{token.text} ... {passive_verb}"

                    findings.append({
                        "clause_id": clause_id,
                        "matched_text": matched,
                        "full_text": sent_text[:200],
                        "issue": "Passive voice — unclear who is responsible",
                        "suggestion": "Rewrite in active voice specifying the responsible party.",
                        "confidence": 0.90,  # Higher confidence from dep parsing
                    })
            return findings

        except Exception as e:
            logger.debug(f"spaCy passive detection failed, using regex fallback: {e}")

    # Regex fallback
    for pattern in PASSIVE_PATTERNS_FALLBACK:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            findings.append({
                "clause_id": clause_id,
                "matched_text": m.group(),
                "full_text": text[:200],
                "issue": "Passive voice — unclear who is responsible",
                "suggestion": "Rewrite in active voice specifying the responsible party.",
                "confidence": 0.85,
            })

    return findings


def _detect_passive_hindi(text: str, clause_id: int) -> List[Dict]:
    """
    Detect passive constructions in Hindi using Stanza dependency labels
    and passive form regex patterns.
    """
    findings = []
    seen_spans = set()

    # ── Layer 1: Stanza dependency parsing ──
    stanza_nlp = _get_stanza()
    if stanza_nlp is not None:
        try:
            doc = stanza_nlp(text[:5000])
            for sent in doc.sentences:
                sent_text = sent.text.strip()
                for word in sent.words:
                    if word.deprel in ("nsubj:pass", "aux:pass"):
                        if sent_text not in seen_spans:
                            seen_spans.add(sent_text)
                            findings.append({
                                "clause_id": clause_id,
                                "matched_text": word.text,
                                "full_text": sent_text[:200],
                                "issue": "कर्मवाच्य (Passive voice) — जिम्मेदार पक्ष अस्पष्ट",
                                "suggestion": "कर्तृवाच्य में लिखें और जिम्मेदार पक्ष स्पष्ट करें।",
                                "confidence": 0.88,
                            })
        except Exception as e:
            logger.debug(f"Stanza passive detection failed: {e}")

    # ── Layer 2: Regex passive pattern matching (covers cases Stanza may miss) ──
    for pattern in HINDI_PASSIVE_PATTERNS:
        for match in re.finditer(pattern, text):
            # Get surrounding context
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()

            if context not in seen_spans:
                seen_spans.add(context)
                findings.append({
                    "clause_id": clause_id,
                    "matched_text": match.group(),
                    "full_text": context[:200],
                    "issue": "कर्मवाच्य (Passive voice) — जिम्मेदार पक्ष अस्पष्ट",
                    "suggestion": "कर्तृवाच्य में लिखें और जिम्मेदार पक्ष स्पष्ट करें।",
                    "confidence": 0.80,
                })

    return findings
