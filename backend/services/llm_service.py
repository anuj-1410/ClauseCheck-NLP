"""
ClauseCheck – LLM Service
Wrapper for Groq API (Llama 3) for plain English translation,
Q&A chatbot, negotiation suggestions, and what-if simulation.
"""

import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_client = None
_model = "llama-3.3-70b-versatile"


def initialize(api_key: str):
    """Initialize the Groq client."""
    global _client
    if not api_key or api_key == "your-groq-api-key":
        logger.info("Groq API key not configured. LLM features will be unavailable.")
        return

    try:
        from groq import Groq
        _client = Groq(api_key=api_key)
        logger.info("✅ Groq LLM client initialized.")
    except ImportError:
        logger.warning("groq package not installed. LLM features unavailable.")
    except Exception as e:
        logger.warning(f"Failed to initialize Groq: {e}")


def is_available() -> bool:
    return _client is not None


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Make a call to the Groq LLM."""
    if not _client:
        return "[LLM unavailable – configure GROQ_API_KEY in .env]"

    try:
        response = _client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"[LLM Error: {str(e)}]"


def _is_llm_error_response(text: str) -> bool:
    """Check whether the model returned an internal error sentinel string."""
    return text.startswith("[LLM unavailable") or text.startswith("[LLM Error:")


def _require_llm_success(text: str) -> str:
    """Raise a runtime error when the LLM call failed so callers can fall back cleanly."""
    if not _is_llm_error_response(text):
        return text

    if text.startswith("[LLM Error:") and text.endswith("]"):
        message = text[len("[LLM Error:"):-1].strip()
    else:
        message = text.strip("[]")
    raise RuntimeError(message)


def translate_to_plain_english(clause_text: str, language: str = "en") -> str:
    """Convert a legal clause into simple, everyday language."""
    lang_note = " The clause is in Hindi, translate to simple Hindi." if language == "hi" else ""
    system = (
        "You are a legal simplifier. Convert legal jargon to 8th-grade reading level. "
        "Keep the legal MEANING accurate but make it crystal clear to a non-lawyer. "
        "Be concise — 2-3 sentences max. Do NOT add legal advice."
        f"{lang_note}"
    )
    response = _call_llm(system, f"Simplify this legal clause:\n\n\"{clause_text}\"", max_tokens=300)
    return _require_llm_success(response)


def translate_text(text: str, target_language: str, source_language: Optional[str] = None) -> str:
    """Translate a UI-facing text fragment while preserving formatting and meaning."""
    if not text or not text.strip():
        return text

    target_label = _language_label(target_language)
    source_label = _language_label(source_language) if source_language else "the source language"
    system = (
        "You are a precise translator for legal-analysis UI text. "
        "Preserve markdown, numbering, bullets, quoted excerpts, and existing structure. "
        "Translate only the content. Do not add explanations."
    )
    user = (
        f"Translate the following text from {source_label} to {target_label}. "
        "Return only the translated text.\n\n"
        f"{text}"
    )
    response = _call_llm(system, user, max_tokens=700)
    return _require_llm_success(response)


def translate_texts(
    texts: List[str],
    target_language: str,
    source_language: Optional[str] = None,
    chunk_size: int = 6,
) -> List[str]:
    """Translate a list of texts efficiently in small batches."""
    if not texts:
        return []

    translated = list(texts)
    pending_indexes = [index for index, text in enumerate(texts) if text and text.strip()]

    for start in range(0, len(pending_indexes), chunk_size):
        chunk_indexes = pending_indexes[start:start + chunk_size]
        payload = [texts[index] for index in chunk_indexes]
        translated_chunk = _translate_text_batch(payload, target_language, source_language)
        for index, translated_text in zip(chunk_indexes, translated_chunk):
            translated[index] = translated_text

    return translated


def answer_question(question: str, contract_text: str, language: str = "en") -> str:
    """Answer a question about the contract using RAG-style context."""
    system = (
        "You are a legal contract Q&A assistant. Answer questions ONLY based on the contract text provided. "
        "If the answer isn't in the contract, say so clearly. "
        "Cite the exact relevant text from the contract in your answer. "
        "Be clear, concise, and helpful. Do NOT provide legal advice — just explain what the contract says. "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )
    user = f"CONTRACT TEXT:\n{contract_text[:8000]}\n\nQUESTION: {question}"
    response = _call_llm(system, user, max_tokens=800)
    return _require_llm_success(response)


def suggest_negotiation(clause_text: str, risk_type: str, severity: str) -> str:
    """Generate negotiation suggestions for a risky clause."""
    system = (
        "You are a legal negotiation advisor. For the given risky clause, provide:\n"
        "1. WHY this clause is problematic (1 sentence)\n"
        "2. HOW to negotiate it (2-3 specific points)\n"
        "3. ALTERNATIVE clause language suggestion (a rewritten version)\n"
        "Be practical and actionable. Do NOT give legal advice — give negotiation strategies."
    )
    user = (
        f"CLAUSE: \"{clause_text}\"\n"
        f"RISK TYPE: {risk_type.replace('_', ' ')}\n"
        f"SEVERITY: {severity}\n\n"
        "Provide negotiation guidance."
    )
    response = _call_llm(system, user, max_tokens=600)
    return _require_llm_success(response)


def simulate_what_if(original_clause: str, modified_clause: str, contract_context: str = "") -> str:
    """Simulate what-if scenario for clause modification."""
    system = (
        "You are a legal risk analyst. Compare the original clause with the modified version. "
        "Analyze:\n"
        "1. How the RISK level changed (increased/decreased/same)\n"
        "2. What IMPLICATIONS the change has for each party\n"
        "3. Whether the modification is RECOMMENDED or not\n"
        "Be specific and analytical. Use bullet points."
    )
    user = (
        f"ORIGINAL CLAUSE:\n\"{original_clause}\"\n\n"
        f"MODIFIED CLAUSE:\n\"{modified_clause}\"\n\n"
        "Analyze the impact of this change."
    )
    response = _call_llm(system, user, max_tokens=600)
    return _require_llm_success(response)


def generate_smart_summary(text: str, language: str = "en") -> str:
    """Generate an LLM-powered concise summary of the contract."""
    system = (
        "You are a legal document summarizer. Create a clear, structured summary of this contract. "
        "Include: parties involved, purpose, key terms, important dates, and notable clauses. "
        "Use bullet points. Keep it under 200 words. "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )
    response = _call_llm(system, f"Summarize this legal document:\n\n{text[:6000]}", max_tokens=500)
    return _require_llm_success(response)


def _translate_text_batch(
    texts: List[str],
    target_language: str,
    source_language: Optional[str] = None,
) -> List[str]:
    """Translate a batch of texts and return them in the same order."""
    if not texts:
        return []

    target_label = _language_label(target_language)
    source_label = _language_label(source_language) if source_language else "the source language"
    system = (
        "You are a precise translator for legal-analysis UI text. "
        "Translate each string in the JSON array to the requested target language. "
        "Preserve markdown, numbering, bullets, and quoted excerpts. "
        "Return only a JSON array of translated strings in the same order."
    )
    user = (
        f"Translate the following JSON array from {source_label} to {target_label}. "
        "Return only a JSON array with the same number of items and in the same order.\n\n"
        f"{json.dumps(texts, ensure_ascii=False)}"
    )

    max_tokens = min(2800, 300 + sum(len(text.split()) for text in texts) * 3)
    response = _require_llm_success(_call_llm(system, user, max_tokens=max_tokens))
    parsed = _parse_json_array(response)
    if parsed is not None and len(parsed) == len(texts):
        return parsed

    logger.warning("Batch translation fallback triggered due to non-JSON or mismatched response.")
    return [translate_text(text, target_language, source_language) for text in texts]


def _parse_json_array(raw_text: str) -> Optional[List[str]]:
    """Extract and parse a JSON array from a model response."""
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None

    try:
        parsed = json.loads(cleaned[start:end + 1])
    except Exception:
        return None

    if not isinstance(parsed, list):
        return None

    return [str(item) for item in parsed]


def _language_label(language: Optional[str]) -> str:
    """Map short language codes to human-readable labels for prompts."""
    normalized = (language or "").strip().lower()
    if normalized in {"hi", "hindi"}:
        return "Hindi"
    return "English"
