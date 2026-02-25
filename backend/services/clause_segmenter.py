"""
ClauseCheck – Clause Segmentation Service
Breaks legal documents into logical clauses using pattern matching
and sentence boundary detection.
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Regex patterns for legal section numbering
# ──────────────────────────────────────────────
SECTION_PATTERNS = [
    # "1.", "1.1", "1.1.1", etc.
    r"(?:^|\n)\s*(\d+(?:\.\d+)*)\s*[\.:\)]\s*",
    # "(a)", "(b)", "(i)", "(ii)", etc.
    r"(?:^|\n)\s*\(([a-z]+|[ivxlc]+)\)\s*",
    # "Section 1", "Article 2", "Clause 3"
    r"(?:^|\n)\s*(?:Section|Article|Clause|Part|Schedule)\s+(\d+[A-Za-z]*)",
    # Roman numerals: "I.", "II.", "III."
    r"(?:^|\n)\s*([IVXLC]+)\s*[\.:\)]\s*",
]

# Hindi section patterns
HINDI_SECTION_PATTERNS = [
    r"(?:^|\n)\s*(?:धारा|अनुच्छेद|खंड|भाग)\s+(\d+)",
    r"(?:^|\n)\s*(\d+(?:\.\d+)*)\s*[\.:\)]\s*",
]


def segment_clauses(text: str, language: str = "en") -> List[Dict]:
    """
    Segment a legal document into individual clauses.

    Args:
        text: Full document text
        language: 'en' or 'hi'

    Returns:
        List of clause dicts with 'id', 'text', 'section_number'
    """
    if not text.strip():
        return []

    patterns = HINDI_SECTION_PATTERNS if language == "hi" else SECTION_PATTERNS

    # Try section-based segmentation first
    clauses = _segment_by_sections(text, patterns)

    # If no numbered sections found, fall back to sentence-based segmentation
    if len(clauses) <= 1:
        clauses = _segment_by_sentences(text)

    # Post-process: merge very short clauses with the next one
    clauses = _merge_short_clauses(clauses)

    logger.info(f"Segmented document into {len(clauses)} clauses.")
    return clauses


def _segment_by_sections(text: str, patterns: List[str]) -> List[Dict]:
    """Split text by numbered section patterns."""
    # Find all section boundaries
    boundaries = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            boundaries.append({
                "start": match.start(),
                "section": match.group(1) if match.lastindex else "",
                "match_end": match.end()
            })

    if not boundaries:
        return [{"id": 1, "text": text.strip(), "section_number": ""}]

    # Sort by position
    boundaries.sort(key=lambda x: x["start"])

    # Remove duplicate/overlapping boundaries
    filtered = [boundaries[0]]
    for b in boundaries[1:]:
        if b["start"] - filtered[-1]["start"] > 20:
            filtered.append(b)
    boundaries = filtered

    # Extract clauses between boundaries
    clauses = []
    for i, boundary in enumerate(boundaries):
        start = boundary["match_end"]
        end = boundaries[i + 1]["start"] if i + 1 < len(boundaries) else len(text)
        clause_text = text[start:end].strip()

        if clause_text:
            clauses.append({
                "id": i + 1,
                "text": clause_text,
                "section_number": boundary["section"]
            })

    return clauses


def _segment_by_sentences(text: str) -> List[Dict]:
    """
    Fall back: split by sentence boundaries.
    Groups sentences into clause-sized chunks.
    """
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?।])\s+', text)

    clauses = []
    current_clause = []
    current_length = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        current_clause.append(sent)
        current_length += len(sent)

        # Group ~2-4 sentences per clause, or split on very long sentences
        if current_length > 200 or len(current_clause) >= 3:
            clauses.append({
                "id": len(clauses) + 1,
                "text": " ".join(current_clause),
                "section_number": ""
            })
            current_clause = []
            current_length = 0

    # Add remaining sentences
    if current_clause:
        clauses.append({
            "id": len(clauses) + 1,
            "text": " ".join(current_clause),
            "section_number": ""
        })

    return clauses


def _merge_short_clauses(clauses: List[Dict], min_length: int = 30) -> List[Dict]:
    """Merge very short clauses into the next clause."""
    if len(clauses) <= 1:
        return clauses

    merged = []
    buffer = ""

    for clause in clauses:
        if len(clause["text"]) < min_length and buffer == "":
            buffer = clause["text"]
        elif buffer:
            clause["text"] = buffer + " " + clause["text"]
            clause["id"] = len(merged) + 1
            merged.append(clause)
            buffer = ""
        else:
            clause["id"] = len(merged) + 1
            merged.append(clause)

    # If buffer still has content, append to last clause
    if buffer and merged:
        merged[-1]["text"] += " " + buffer
    elif buffer:
        merged.append({"id": 1, "text": buffer, "section_number": ""})

    return merged
