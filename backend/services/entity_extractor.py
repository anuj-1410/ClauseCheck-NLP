"""
ClauseCheck – Named Entity Extraction Service
Extracts parties, dates, monetary values, durations, and legal references
using spaCy (English) and Stanza (Hindi).

Upgrades:
  - English: en_core_web_trf (transformer-based) with fallback to en_core_web_sm
  - Hindi: Stanza NER + Legal regex + Legal gazetteer dictionary (Layer 1-3)
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global NLP model references (loaded lazily)
_spacy_nlp = None
_stanza_nlp = None

# ──────────────────────────────────────────────
# Hindi Legal Gazetteer — well-known Indian legal acts
# ──────────────────────────────────────────────
HINDI_LEGAL_GAZETTEER = [
    "भारतीय अनुबंध अधिनियम, 1872",
    "भारतीय अनुबंध अधिनियम",
    "सूचना प्रौद्योगिकी अधिनियम, 2000",
    "सूचना प्रौद्योगिकी अधिनियम",
    "उपभोक्ता संरक्षण अधिनियम, 2019",
    "उपभोक्ता संरक्षण अधिनियम",
    "कंपनी अधिनियम, 2013",
    "कंपनी अधिनियम",
    "मध्यस्थता एवं सुलह अधिनियम, 1996",
    "मध्यस्थता एवं सुलह अधिनियम",
    "औद्योगिक विवाद अधिनियम, 1947",
    "औद्योगिक विवाद अधिनियम",
    "भारतीय दंड संहिता",
    "भारतीय स्टाम्प अधिनियम, 1899",
    "भारतीय स्टाम्प अधिनियम",
    "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम, 2023",
    "पेटेंट अधिनियम, 1970",
    "कॉपीराइट अधिनियम, 1957",
    "ट्रेडमार्क अधिनियम, 1999",
    "विशिष्ट अनुतोष अधिनियम, 1963",
    "भारतीय साक्ष्य अधिनियम",
    "सिविल प्रक्रिया संहिता",
    "दीवानी प्रक्रिया संहिता",
]

# Hindi legal reference regex patterns
HINDI_LEGAL_PATTERNS = [
    r"धारा\s+\d+[क-ह]*(?:\s+(?:का|के|की))?\s*(?:[\w\s]+अधिनियम(?:\s*,?\s*\d{4})?)?",
    r"अनुच्छेद\s+\d+[क-ह]*",
    r"(?:[\w\s]+)?अधिनियम(?:\s*,?\s*\d{4})?",
    r"नियम\s+\d+",
    r"उप-धारा\s*\(\s*\d+\s*\)",
]


def _get_spacy():
    """Lazy-load spaCy English model. Prefer en_core_web_trf, fallback to en_core_web_sm."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            # Try transformer model first
            try:
                _spacy_nlp = spacy.load("en_core_web_trf")
                logger.info("spaCy en_core_web_trf (transformer) model loaded.")
            except OSError:
                _spacy_nlp = spacy.load("en_core_web_sm")
                logger.info("en_core_web_trf not found. Using en_core_web_sm fallback.")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            return None
    return _spacy_nlp


def _get_stanza():
    """Lazy-load Stanza Hindi model."""
    global _stanza_nlp
    if _stanza_nlp is None:
        try:
            import stanza
            _stanza_nlp = stanza.Pipeline("hi", processors="tokenize,ner", verbose=False)
            logger.info("Stanza Hindi model loaded.")
        except Exception as e:
            logger.error(f"Failed to load Stanza model: {e}")
            return None
    return _stanza_nlp


def extract_entities(text: str, language: str = "en") -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract named entities from text.

    Returns:
        Dictionary with entity categories:
        - parties: persons and organizations
        - dates: date references
        - monetary_values: money amounts
        - durations: time periods
        - legal_references: law/act references
    """
    if language == "hi":
        entities = _extract_entities_hindi(text)
    else:
        entities = _extract_entities_english(text)

    # Supplement with regex-based extraction
    entities = _enrich_with_regex(text, entities, language)

    return entities


def _extract_entities_english(text: str) -> Dict[str, List[Dict]]:
    """Extract entities using spaCy for English."""
    nlp = _get_spacy()
    result = {
        "parties": [],
        "dates": [],
        "monetary_values": [],
        "durations": [],
        "legal_references": []
    }

    if nlp is None:
        return result

    doc = nlp(text[:100000])  # Limit for performance

    seen = set()
    for ent in doc.ents:
        key = (ent.label_, ent.text.strip())
        if key in seen or not ent.text.strip():
            continue
        seen.add(key)

        entity_data = {"text": ent.text.strip(), "label": ent.label_}

        if ent.label_ in ("PERSON", "ORG"):
            result["parties"].append(entity_data)
        elif ent.label_ == "DATE":
            result["dates"].append(entity_data)
        elif ent.label_ == "MONEY":
            result["monetary_values"].append(entity_data)
        elif ent.label_ in ("TIME", "QUANTITY"):
            result["durations"].append(entity_data)
        elif ent.label_ == "LAW":
            result["legal_references"].append(entity_data)

    return result


def _extract_entities_hindi(text: str) -> Dict[str, List[Dict]]:
    """
    Extract entities using 3-layer approach for Hindi:
      Layer 1: Stanza NER
      Layer 2: Hindi legal regex patterns
      Layer 3: Legal gazetteer dictionary
    """
    result = {
        "parties": [],
        "dates": [],
        "monetary_values": [],
        "durations": [],
        "legal_references": []
    }

    # ── Layer 1: Stanza NER ──
    nlp = _get_stanza()
    if nlp is not None:
        try:
            doc = nlp(text[:50000])
            seen = set()
            for sentence in doc.sentences:
                for ent in sentence.ents:
                    key = (ent.type, ent.text.strip())
                    if key in seen or not ent.text.strip():
                        continue
                    seen.add(key)

                    entity_data = {"text": ent.text.strip(), "label": ent.type}

                    if ent.type in ("PER", "ORG"):
                        result["parties"].append(entity_data)
                    elif ent.type == "DATE":
                        result["dates"].append(entity_data)
                    elif ent.type == "MONEY":
                        result["monetary_values"].append(entity_data)
        except Exception as e:
            logger.error(f"Stanza NER failed: {e}")

    # ── Layer 2: Hindi legal regex extraction ──
    existing_legal = {e["text"] for e in result["legal_references"]}
    for pattern in HINDI_LEGAL_PATTERNS:
        for match in re.finditer(pattern, text):
            matched = match.group().strip()
            if matched and len(matched) > 3 and matched not in existing_legal:
                result["legal_references"].append({"text": matched, "label": "LAW"})
                existing_legal.add(matched)

    # ── Layer 3: Legal gazetteer dictionary lookup ──
    for act_name in HINDI_LEGAL_GAZETTEER:
        if act_name in text and act_name not in existing_legal:
            result["legal_references"].append({"text": act_name, "label": "LAW"})
            existing_legal.add(act_name)

    return result


def _enrich_with_regex(
    text: str,
    entities: Dict[str, List[Dict]],
    language: str
) -> Dict[str, List[Dict]]:
    """Enrich entity extraction with regex patterns for legal documents."""

    # Date patterns
    date_patterns = [
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    ]

    # Hindi date patterns
    if language == "hi":
        date_patterns.append(
            r"\d{1,2}\s+(?:जनवरी|फ़रवरी|फरवरी|मार्च|अप्रैल|मई|जून|"
            r"जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर)\s*,?\s*\d{4}"
        )

    existing_dates = {e["text"] for e in entities["dates"]}
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group() not in existing_dates:
                entities["dates"].append({"text": match.group(), "label": "DATE"})
                existing_dates.add(match.group())

    # Monetary patterns
    money_patterns = [
        r"(?:Rs\.?|INR|₹|USD|\$|€)\s*[\d,]+(?:\.\d{1,2})?(?:\s*(?:crore|lakh|million|billion))?",
        r"[\d,]+(?:\.\d{1,2})?\s*(?:rupees|dollars|euros)",
    ]
    # Hindi monetary patterns
    if language == "hi":
        money_patterns.append(r"(?:₹|रु\.?|रुपये)\s*[\d,]+(?:\.\d{1,2})?(?:\s*(?:करोड़|लाख))?")

    existing_money = {e["text"] for e in entities["monetary_values"]}
    for pattern in money_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group() not in existing_money:
                entities["monetary_values"].append({"text": match.group(), "label": "MONEY"})
                existing_money.add(match.group())

    # Duration patterns
    duration_patterns = [
        r"\b\d+\s*(?:days?|weeks?|months?|years?|business\s+days?)\b",
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|"
        r"thirty|sixty|ninety)\s*(?:days?|weeks?|months?|years?)\b",
    ]
    # Hindi duration patterns
    if language == "hi":
        duration_patterns.append(r"\d+\s*(?:दिन|सप्ताह|महीने|महीना|वर्ष|साल)")

    existing_durations = {e["text"] for e in entities["durations"]}
    for pattern in duration_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group() not in existing_durations:
                entities["durations"].append({"text": match.group(), "label": "DURATION"})
                existing_durations.add(match.group())

    # Legal reference patterns
    legal_patterns = [
        r"(?:Indian\s+)?(?:Contract\s+Act|Companies\s+Act|IT\s+Act|"
        r"Consumer\s+Protection\s+Act|Arbitration\s+Act|"
        r"Information\s+Technology\s+Act|GDPR|CCPA)(?:\s*,?\s*\d{4})?",
        r"Section\s+\d+[A-Za-z]*(?:\s+of\s+the\s+[\w\s]+Act(?:\s*,?\s*\d{4})?)?",
    ]

    existing_legal = {e["text"] for e in entities["legal_references"]}
    for pattern in legal_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group() not in existing_legal:
                entities["legal_references"].append({"text": match.group(), "label": "LAW"})
                existing_legal.add(match.group())

    return entities
