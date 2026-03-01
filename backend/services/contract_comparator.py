"""
ClauseCheck – Contract Comparison Service
Compares two legal documents clause-by-clause, detects changes,
and computes risk deltas.

Upgrades:
  - Replaced SequenceMatcher with multilingual sentence-transformer embeddings
  - Semantic clause matching: Hindi↔Hindi, English↔English, Hindi↔English
  - SequenceMatcher kept as fallback if embeddings unavailable
"""

import logging
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

import numpy as np

from services.clause_segmenter import segment_clauses
from services.risk_detector import detect_risks, calculate_overall_risk_score
from services.compliance_checker import check_compliance

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.4  # Below this = completely different clauses
SEMANTIC_THRESHOLD = 0.55   # Semantic similarity threshold

# Lazy-loaded semantic model
_embed_model = None


def _get_embedding_model():
    """Lazy-load sentence-transformer model for semantic comparison."""
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer(
                "paraphrase-multilingual-mpnet-base-v2"
            )
            logger.info("Semantic model loaded for contract comparison.")
        except Exception as e:
            logger.warning(f"Failed to load semantic model: {e}. Using lexical fallback.")
            _embed_model = False  # Mark as failed
    return _embed_model if _embed_model is not False else None


def compare_contracts(
    text1: str, text2: str,
    name1: str = "Document 1", name2: str = "Document 2",
    language: str = "en"
) -> Dict[str, Any]:
    """
    Compare two contract texts clause-by-clause.

    Returns:
        Dict with:
        - added: clauses in doc2 but not doc1
        - removed: clauses in doc1 but not doc2
        - modified: clauses that changed between versions
        - unchanged: clauses that are the same
        - risk_delta: change in risk score
        - compliance_delta: change in compliance score
        - summary: overall comparison summary
    """
    clauses1 = segment_clauses(text1, language)
    clauses2 = segment_clauses(text2, language)

    # Analyze risks for both
    risks1 = detect_risks(clauses1, language)
    risks2 = detect_risks(clauses2, language)
    risk_score1 = calculate_overall_risk_score(risks1)
    risk_score2 = calculate_overall_risk_score(risks2)

    compliance1 = check_compliance(clauses1, text1, language)
    compliance2 = check_compliance(clauses2, text2, language)

    # Match clauses between documents (semantic or lexical)
    matches = _match_clauses(clauses1, clauses2)

    added = []
    removed = []
    modified = []
    unchanged = []

    matched_doc2_ids = set()

    for c1_idx, c2_idx, similarity in matches:
        if c2_idx is not None:
            matched_doc2_ids.add(c2_idx)

        if c2_idx is None:
            # Clause removed in doc2
            removed.append({
                "clause": clauses1[c1_idx],
                "document": name1,
            })
        elif similarity > 0.95:
            # Unchanged
            unchanged.append({
                "clause_doc1": clauses1[c1_idx],
                "clause_doc2": clauses2[c2_idx],
                "similarity": round(similarity, 2),
            })
        else:
            # Modified
            diff = _compute_text_diff(
                clauses1[c1_idx]["text"],
                clauses2[c2_idx]["text"]
            )
            modified.append({
                "clause_doc1": clauses1[c1_idx],
                "clause_doc2": clauses2[c2_idx],
                "similarity": round(similarity, 2),
                "changes": diff,
            })

    # Find added clauses (in doc2 but not matched)
    for i, clause in enumerate(clauses2):
        if i not in matched_doc2_ids:
            added.append({
                "clause": clause,
                "document": name2,
            })

    # risk/compliance deltas
    risk_delta = risk_score2 - risk_score1
    compliance_delta = compliance2["compliance_score"] - compliance1["compliance_score"]

    # Power shift
    if risk_delta > 10:
        power_shift = f"⚠️ Risk increased by {risk_delta} points in {name2}."
    elif risk_delta < -10:
        power_shift = f"✅ Risk decreased by {abs(risk_delta)} points in {name2}."
    else:
        power_shift = "↔️ Risk level is similar between both versions."

    summary = (
        f"Compared {len(clauses1)} clauses ({name1}) vs {len(clauses2)} clauses ({name2}). "
        f"{len(added)} added, {len(removed)} removed, {len(modified)} modified, "
        f"{len(unchanged)} unchanged. {power_shift}"
    )

    logger.info(summary)

    return {
        "document1": {"name": name1, "clause_count": len(clauses1),
                       "risk_score": risk_score1, "compliance_score": compliance1["compliance_score"]},
        "document2": {"name": name2, "clause_count": len(clauses2),
                       "risk_score": risk_score2, "compliance_score": compliance2["compliance_score"]},
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "risk_delta": risk_delta,
        "compliance_delta": compliance_delta,
        "power_shift": power_shift,
        "summary": summary,
    }


def _match_clauses(
    clauses1: List[Dict], clauses2: List[Dict]
) -> List[Tuple[int, int, float]]:
    """
    Match clauses between two documents.
    Uses semantic embeddings if available, falls back to SequenceMatcher.
    """
    model = _get_embedding_model()

    if model is not None and len(clauses1) > 0 and len(clauses2) > 0:
        return _match_clauses_semantic(clauses1, clauses2, model)
    else:
        return _match_clauses_lexical(clauses1, clauses2)


def _match_clauses_semantic(
    clauses1: List[Dict],
    clauses2: List[Dict],
    model: Any
) -> List[Tuple[int, int, float]]:
    """Match clauses using semantic embeddings (cross-lingual capable)."""
    try:
        texts1 = [c["text"][:500] for c in clauses1]
        texts2 = [c["text"][:500] for c in clauses2]

        embs1 = model.encode(texts1, convert_to_numpy=True)
        embs2 = model.encode(texts2, convert_to_numpy=True)

        # Normalize embeddings
        norms1 = np.linalg.norm(embs1, axis=1, keepdims=True)
        norms2 = np.linalg.norm(embs2, axis=1, keepdims=True)
        embs1_normed = embs1 / np.maximum(norms1, 1e-8)
        embs2_normed = embs2 / np.maximum(norms2, 1e-8)

        # Compute similarity matrix
        sim_matrix = np.dot(embs1_normed, embs2_normed.T)

        matches = []
        used_c2 = set()

        for i in range(len(clauses1)):
            best_match = None
            best_sim = 0

            for j in range(len(clauses2)):
                if j in used_c2:
                    continue
                sim = float(sim_matrix[i, j])
                if sim > best_sim:
                    best_sim = sim
                    best_match = j

            if best_match is not None and best_sim >= SEMANTIC_THRESHOLD:
                matches.append((i, best_match, best_sim))
                used_c2.add(best_match)
            else:
                matches.append((i, None, 0.0))

        return matches

    except Exception as e:
        logger.warning(f"Semantic matching failed: {e}. Falling back to lexical.")
        return _match_clauses_lexical(clauses1, clauses2)


def _match_clauses_lexical(
    clauses1: List[Dict], clauses2: List[Dict]
) -> List[Tuple[int, int, float]]:
    """Match clauses using SequenceMatcher (lexical similarity fallback)."""
    matches = []
    used_c2 = set()

    for i, c1 in enumerate(clauses1):
        best_match = None
        best_sim = 0

        for j, c2 in enumerate(clauses2):
            if j in used_c2:
                continue
            sim = SequenceMatcher(None, c1["text"].lower(), c2["text"].lower()).ratio()
            if sim > best_sim:
                best_sim = sim
                best_match = j

        if best_match is not None and best_sim >= SIMILARITY_THRESHOLD:
            matches.append((i, best_match, best_sim))
            used_c2.add(best_match)
        else:
            matches.append((i, None, 0.0))

    return matches


def _compute_text_diff(text1: str, text2: str) -> List[Dict]:
    """Compute word-level differences between two texts."""
    words1 = text1.split()
    words2 = text2.split()
    sm = SequenceMatcher(None, words1, words2)

    changes = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            changes.append({
                "type": "modified",
                "old": " ".join(words1[i1:i2]),
                "new": " ".join(words2[j1:j2]),
            })
        elif tag == "delete":
            changes.append({
                "type": "removed",
                "old": " ".join(words1[i1:i2]),
                "new": "",
            })
        elif tag == "insert":
            changes.append({
                "type": "added",
                "old": "",
                "new": " ".join(words2[j1:j2]),
            })

    return changes
