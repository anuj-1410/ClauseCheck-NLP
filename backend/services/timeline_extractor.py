"""
ClauseCheck – Timeline Extractor
Extracts dates, deadlines, durations, and milestones from contract clauses
and structures them into a timeline format for visualization.

Upgrades:
  - Normalize extracted dates to actual datetime objects (ISO format)
  - Added Hindi date patterns (जनवरी, फ़रवरी, मार्च...)
  - Added Hindi deadline patterns (के भीतर, से पहले, तक)
  - Enables timeline sorting and Gantt visualization
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# English month names for date normalization
# ──────────────────────────────────────────────
ENGLISH_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Hindi month names for date normalization
HINDI_MONTHS = {
    "जनवरी": 1, "फ़रवरी": 2, "फरवरी": 2, "मार्च": 3,
    "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7,
    "अगस्त": 8, "सितंबर": 9, "अक्टूबर": 10,
    "नवंबर": 11, "दिसंबर": 12,
}

# ──────────────────────────────────────────────
# Date extraction patterns
# ──────────────────────────────────────────────
DATE_PATTERNS = [
    # DD/MM/YYYY or MM/DD/YYYY
    (r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", "date"),
    # "1 January 2024"
    (r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
     r"September|October|November|December)\s+\d{4})\b", "date"),
    # "January 1, 2024"
    (r"\b((?:January|February|March|April|May|June|July|August|"
     r"September|October|November|December)\s+\d{1,2},?\s+\d{4})\b", "date"),
]

# Hindi date patterns
HINDI_DATE_PATTERNS = [
    (r"(\d{1,2}\s+(?:जनवरी|फ़रवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|"
     r"सितंबर|अक्टूबर|नवंबर|दिसंबर)\s*,?\s*\d{4})", "date"),
]

DEADLINE_PATTERNS = [
    (r"within\s+(\d+\s*(?:days?|weeks?|months?|years?|business\s+days?))", "deadline"),
    (r"no\s+later\s+than\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"before\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"on\s+or\s+before\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"not\s+(?:to\s+)?exceed\s+(\d+\s*(?:days?|months?|years?))", "deadline"),
]

# Hindi deadline patterns
HINDI_DEADLINE_PATTERNS = [
    (r"(\d+\s*(?:दिन|सप्ताह|महीने|महीना|वर्ष|साल))\s+के\s+भीतर", "deadline"),
    (r"(.+?)\s+से\s+पहले(?:\s|।|$)", "deadline"),
    (r"(.+?)\s+तक(?:\s|।|$)", "deadline"),
]

DURATION_PATTERNS = [
    (r"(?:for\s+)?(?:a\s+)?(?:period|term|duration)\s+of\s+(\d+\s*(?:days?|weeks?|months?|years?))", "duration"),
    (r"(\d+)[\s-](?:year|month|week|day)\s+(?:term|period|contract|agreement)", "duration"),
    (r"(?:valid|effective)\s+(?:for|until)\s+(.+?)(?:\.|,|;|$)", "duration"),
]

RENEWAL_PATTERNS = [
    (r"(?:auto(?:matic(?:ally)?)?[\s-]+)?renew(?:ed|al)?\s+(?:for\s+)?(.+?)(?:\.|,|;|$)", "renewal"),
]

NOTICE_PATTERNS = [
    (r"(\d+\s*(?:days?|weeks?|months?))\s*(?:prior\s+)?(?:written\s+)?notice", "notice"),
    (r"notice\s+(?:period\s+)?(?:of\s+)?(\d+\s*(?:days?|weeks?|months?))", "notice"),
]

# Event type categorization
EVENT_CATEGORIES = {
    "date": {"icon": "📅", "color": "#3b82f6", "label": "Date"},
    "deadline": {"icon": "⏰", "color": "#ef4444", "label": "Deadline"},
    "duration": {"icon": "📏", "color": "#8b5cf6", "label": "Duration"},
    "renewal": {"icon": "🔄", "color": "#f59e0b", "label": "Renewal"},
    "notice": {"icon": "📢", "color": "#06b6d4", "label": "Notice Period"},
    "payment": {"icon": "💰", "color": "#22c55e", "label": "Payment"},
    "termination": {"icon": "🚫", "color": "#dc2626", "label": "Termination"},
}


def extract_timeline(
    clauses: List[Dict],
    entities: Dict[str, Any],
    obligations: List[Dict]
) -> Dict[str, Any]:
    """
    Extract timeline events from clauses, entities, and obligations.

    Returns:
        Dict with:
        - events: list of timeline events (with parsed_date where available)
        - categories: event category metadata
        - total_events: count
    """
    events = []
    language = "en"  # Will be detected per-clause

    # Detect if text is Hindi
    all_text = " ".join(c.get("text", "") for c in clauses[:5])
    if re.search(r'[\u0900-\u097F]', all_text):
        language = "hi"

    for clause in clauses:
        text = clause["text"]
        clause_id = clause["id"]
        section = clause.get("section_number", "")

        # Extract dates (English)
        for pattern, event_type in DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                parsed = _normalize_date(match.group(1))
                events.append(_build_event(
                    match.group(1), event_type, clause_id, section,
                    f"Date reference in clause #{clause_id}", text[:150],
                    parsed_date=parsed
                ))

        # Extract dates (Hindi)
        if language == "hi":
            for pattern, event_type in HINDI_DATE_PATTERNS:
                for match in re.finditer(pattern, text):
                    parsed = _normalize_hindi_date(match.group(1))
                    events.append(_build_event(
                        match.group(1), event_type, clause_id, section,
                        f"दिनांक संदर्भ खंड #{clause_id}", text[:150],
                        parsed_date=parsed
                    ))

        # Extract deadlines (English)
        for pattern, event_type in DEADLINE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1).strip(), event_type, clause_id, section,
                    f"Deadline: {match.group(1).strip()}", text[:150]
                ))

        # Extract deadlines (Hindi)
        if language == "hi":
            for pattern, event_type in HINDI_DEADLINE_PATTERNS:
                for match in re.finditer(pattern, text):
                    events.append(_build_event(
                        match.group(1).strip(), event_type, clause_id, section,
                        f"समय सीमा: {match.group(1).strip()}", text[:150]
                    ))

        # Extract durations
        for pattern, event_type in DURATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1).strip(), event_type, clause_id, section,
                    f"Duration: {match.group(1).strip()}", text[:150]
                ))

        # Extract renewals
        for pattern, event_type in RENEWAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1).strip(), event_type, clause_id, section,
                    f"Renewal: {match.group(1).strip()}", text[:150]
                ))

        # Extract notice periods
        for pattern, event_type in NOTICE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1).strip(), event_type, clause_id, section,
                    f"Notice period: {match.group(1).strip()}", text[:150]
                ))

        # Detect payment-related events
        if re.search(r"\b(?:payment|pay|invoice|billing|due|remit)\b", text, re.IGNORECASE):
            deadline_match = re.search(
                r"(?:within|by|before|no later than)\s+(.+?)(?:\.|,|;|$)",
                text, re.IGNORECASE
            )
            if deadline_match:
                events.append(_build_event(
                    deadline_match.group(1).strip(), "payment", clause_id, section,
                    f"Payment deadline: {deadline_match.group(1).strip()}", text[:150]
                ))

        # Detect termination-related events
        if re.search(r"\b(?:terminat|expir|end\s+of\s+(?:term|agreement))\b", text, re.IGNORECASE):
            events.append(_build_event(
                "See clause", "termination", clause_id, section,
                "Termination provision", text[:150]
            ))

    # Add entity-derived dates
    for date_entity in entities.get("dates", []):
        parsed = _normalize_date(date_entity["text"])
        events.append({
            "id": len(events) + 1,
            "value": date_entity["text"],
            "type": "date",
            "clause_id": None,
            "section": "",
            "description": f"Referenced date: {date_entity['text']}",
            "context": "",
            "category": EVENT_CATEGORIES["date"],
            "parsed_date": parsed,
        })

    # Deduplicate
    events = _deduplicate_events(events)

    # Sort by parsed date where available
    events = _sort_events_by_date(events)

    logger.info(f"Extracted {len(events)} timeline events.")

    return {
        "events": events,
        "categories": EVENT_CATEGORIES,
        "total_events": len(events),
    }


def _build_event(
    value: str, event_type: str, clause_id: int,
    section: str, description: str, context: str,
    parsed_date: Optional[str] = None
) -> Dict[str, Any]:
    """Build a timeline event dict."""
    return {
        "id": 0,  # Will be assigned after dedup
        "value": value[:100],
        "type": event_type,
        "clause_id": clause_id,
        "section": section,
        "description": description,
        "context": context[:150],
        "category": EVENT_CATEGORIES.get(event_type, EVENT_CATEGORIES["date"]),
        "parsed_date": parsed_date,
    }


def _normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize a date string to ISO format (YYYY-MM-DD).
    Returns None if parsing fails.
    """
    if not date_str:
        return None

    # Try common formats
    formats = [
        "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
        "%d/%m/%y", "%m/%d/%y", "%d-%m-%y", "%m-%d-%y",
        "%d %B %Y", "%B %d, %Y", "%B %d %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip().replace(",", ""), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _normalize_hindi_date(date_str: str) -> Optional[str]:
    """
    Normalize a Hindi date string to ISO format (YYYY-MM-DD).
    Example: "15 जनवरी 2024" → "2024-01-15"
    """
    if not date_str:
        return None

    try:
        # Extract components: day, Hindi month, year
        match = re.match(
            r'(\d{1,2})\s+(\S+)\s*,?\s*(\d{4})',
            date_str.strip()
        )
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))

            month = HINDI_MONTHS.get(month_name)
            if month:
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    return None


def _deduplicate_events(events: List[Dict]) -> List[Dict]:
    """Remove duplicate events."""
    seen = set()
    unique = []
    for ev in events:
        key = (ev["value"], ev["type"], ev.get("clause_id"))
        if key not in seen:
            seen.add(key)
            ev["id"] = len(unique) + 1
            unique.append(ev)
    return unique


def _sort_events_by_date(events: List[Dict]) -> List[Dict]:
    """
    Sort events by parsed_date (those with dates first, then by date).
    Events without dates keep their original order at the end.
    """
    dated = [e for e in events if e.get("parsed_date")]
    undated = [e for e in events if not e.get("parsed_date")]

    dated.sort(key=lambda e: e["parsed_date"])

    result = dated + undated
    # Re-assign IDs
    for i, ev in enumerate(result):
        ev["id"] = i + 1

    return result
