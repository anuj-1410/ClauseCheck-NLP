"""
ClauseCheck – Summarization Service
Generates concise document summaries.

Primary: LLM summarization (handled in analyze.py)
Fallback: TextRank (graph-based extractive summarization)

Upgrade: Replaced TF-IDF with TextRank for better extractive summaries.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Try to use networkx for TextRank
_HAS_NETWORKX = False
try:
    import networkx as nx
    _HAS_NETWORKX = True
except ImportError:
    logger.info("networkx not installed. Using basic scoring fallback.")


def summarize_document(text: str, num_sentences: int = 5) -> str:
    """
    Generate an extractive summary of the document.

    Uses TextRank (graph-based) for better sentence selection.
    Falls back to positional scoring if networkx unavailable.

    Args:
        text: Full document text
        num_sentences: Number of sentences to include in summary

    Returns:
        Summary string
    """
    if not text.strip():
        return "No text available for summarization."

    sentences = _split_sentences(text)

    if len(sentences) <= num_sentences:
        return text.strip()

    if _HAS_NETWORKX:
        summary = _textrank_summarize(sentences, num_sentences)
    else:
        summary = _positional_summarize(sentences, num_sentences)

    logger.info(f"Generated summary: {num_sentences} sentences from {len(sentences)} total.")
    return summary


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Handle both English and Hindi sentence boundaries
    sentences = re.split(r'(?<=[.!?।])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _textrank_summarize(sentences: List[str], num_sentences: int) -> str:
    """
    TextRank-based extractive summarization.
    Builds a sentence similarity graph and ranks by PageRank.
    """
    import numpy as np

    n = len(sentences)
    if n <= num_sentences:
        return " ".join(sentences)

    # Tokenize sentences
    word_sets = [set(_tokenize(s)) for s in sentences]

    # Build similarity matrix
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if not word_sets[i] or not word_sets[j]:
                continue
            # Jaccard-like similarity
            intersection = word_sets[i] & word_sets[j]
            union = word_sets[i] | word_sets[j]
            if union:
                sim = len(intersection) / len(union)
                sim_matrix[i][j] = sim
                sim_matrix[j][i] = sim

    # Build graph
    graph = nx.from_numpy_array(sim_matrix)

    # Run PageRank
    try:
        scores = nx.pagerank(graph, max_iter=200)
    except Exception:
        # Fallback if PageRank fails (e.g., disconnected graph)
        scores = {i: 1.0 for i in range(n)}

    # Boost first and last sentences (important in legal docs)
    scores[0] = scores.get(0, 0) * 1.5
    if n - 1 in scores:
        scores[n - 1] = scores[n - 1] * 1.2
    for i in range(1, min(3, n)):
        scores[i] = scores.get(i, 0) * 1.1

    # Select top-scoring sentences while maintaining document order
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_indices = sorted([idx for idx, _ in ranked[:num_sentences]])

    summary_sentences = [sentences[i] for i in top_indices]
    return " ".join(summary_sentences)


def _positional_summarize(sentences: List[str], num_sentences: int) -> str:
    """
    Basic positional summarization fallback.
    Selects sentences based on position (first, last) and length.
    """
    n = len(sentences)
    scores = []

    for i, sent in enumerate(sentences):
        score = 0.0
        words = _tokenize(sent)
        # Longer sentences tend to be more informative
        score += min(len(words) / 20.0, 1.0)

        # Position boost
        if i == 0:
            score += 2.0
        elif i == n - 1:
            score += 1.5
        elif i < 3:
            score += 1.0

        scores.append((i, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = sorted([idx for idx, _ in scores[:num_sentences]])

    summary_sentences = [sentences[i] for i in top_indices]
    return " ".join(summary_sentences)


def _tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase, remove punctuation, filter stopwords."""
    text = text.lower()
    words = re.findall(r'\b[a-zA-Z\u0900-\u097F]{2,}\b', text)

    # Basic English stopwords
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "both", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "same", "so", "than", "too",
        "very", "and", "but", "or", "if", "this", "that", "these", "those",
        "it", "its", "he", "she", "they", "them", "his", "her", "their",
        "what", "which", "who", "whom"
    }

    return [w for w in words if w not in stopwords]
