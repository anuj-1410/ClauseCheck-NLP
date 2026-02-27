"""
ClauseCheck – Timeline Extractor
Extracts dates, deadlines, durations, and milestones from contract clauses
and structures them into a timeline format for visualization.
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Date extraction patterns
# ──────────────────────────────────────────────
DATE_PATTERNS = [
    # DD/MM/YYYY or MM/DD/YYYY
    (r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", "date"),
    # "January 1, 2024" or "1 January 2024"
    (r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
     r"September|October|November|December)\s+\d{4})\b", "date"),
    (r"\b((?:January|February|March|April|May|June|July|August|"
     r"September|October|November|December)\s+\d{1,2},?\s+\d{4})\b", "date"),
]

DEADLINE_PATTERNS = [
    (r"within\s+(\d+\s*(?:days?|weeks?|months?|years?|business\s+days?))", "deadline"),
    (r"no\s+later\s+than\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"before\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"on\s+or\s+before\s+(.+?)(?:\.|,|;|$)", "deadline"),
    (r"not\s+(?:to\s+)?exceed\s+(\d+\s*(?:days?|months?|years?))", "deadline"),
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
        - events: list of timeline events
        - categories: event category metadata
        - total_events: count
    """
    events = []

    for clause in clauses:
        text = clause["text"]
        clause_id = clause["id"]
        section = clause.get("section_number", "")

        # Extract dates
        for pattern, event_type in DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1), event_type, clause_id, section,
                    f"Date reference in clause #{clause_id}", text[:150]
                ))

        # Extract deadlines
        for pattern, event_type in DEADLINE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(_build_event(
                    match.group(1).strip(), event_type, clause_id, section,
                    f"Deadline: {match.group(1).strip()}", text[:150]
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
        events.append({
            "id": len(events) + 1,
            "value": date_entity["text"],
            "type": "date",
            "clause_id": None,
            "section": "",
            "description": f"Referenced date: {date_entity['text']}",
            "context": "",
            "category": EVENT_CATEGORIES["date"],
        })

    # Deduplicate
    events = _deduplicate_events(events)

    logger.info(f"Extracted {len(events)} timeline events.")

    return {
        "events": events,
        "categories": EVENT_CATEGORIES,
        "total_events": len(events),
    }


def _build_event(
    value: str, event_type: str, clause_id: int,
    section: str, description: str, context: str
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
    }


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
