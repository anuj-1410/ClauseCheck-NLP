"""
ClauseCheck – Summarization Service
Generates concise document summaries using extractive summarization.
"""

import re
import logging
import math
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)


def summarize_document(text: str, num_sentences: int = 5) -> str:
    """
    Generate an extractive summary of the document using TF-IDF scoring.

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

    # Calculate TF-IDF scores for sentences
    scores = _score_sentences(sentences)

    # Select top-scoring sentences while maintaining order
    indexed_scores = list(enumerate(scores))
    indexed_scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = sorted([idx for idx, _ in indexed_scores[:num_sentences]])

    summary_sentences = [sentences[i] for i in top_indices]
    summary = " ".join(summary_sentences)

    logger.info(f"Generated summary: {len(summary_sentences)} sentences from {len(sentences)} total.")
    return summary


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Handle both English and Hindi sentence boundaries
    sentences = re.split(r'(?<=[.!?।])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _score_sentences(sentences: List[str]) -> List[float]:
    """Calculate TF-IDF-based importance score for each sentence."""
    # Tokenize all sentences
    word_lists = [_tokenize(s) for s in sentences]
    all_words = [w for wl in word_lists for w in wl]

    # Term frequency across document
    doc_tf = Counter(all_words)
    num_sentences = len(sentences)

    # Document frequency (how many sentences contain each word)
    df = Counter()
    for wl in word_lists:
        for word in set(wl):
            df[word] += 1

    # Score each sentence
    scores = []
    for i, words in enumerate(word_lists):
        if not words:
            scores.append(0.0)
            continue

        # TF-IDF score
        score = 0.0
        for word in words:
            tf = words.count(word) / len(words)
            idf = math.log(num_sentences / (df[word] + 1)) + 1
            score += tf * idf

        # Normalize by sentence length
        score /= len(words)

        # Boost first and last sentences (usually important in legal docs)
        if i == 0:
            score *= 1.5
        elif i == num_sentences - 1:
            score *= 1.2
        elif i < 3:
            score *= 1.1

        scores.append(score)

    return scores


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
