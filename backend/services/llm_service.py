"""
ClauseCheck – LLM Service
Wrapper for Groq API (Llama 3) for plain English translation,
Q&A chatbot, negotiation suggestions, and what-if simulation.
"""

import logging
from typing import Optional

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


def translate_to_plain_english(clause_text: str, language: str = "en") -> str:
    """Convert a legal clause into simple, everyday language."""
    lang_note = " The clause is in Hindi, translate to simple Hindi." if language == "hi" else ""
    system = (
        "You are a legal simplifier. Convert legal jargon to 8th-grade reading level. "
        "Keep the legal MEANING accurate but make it crystal clear to a non-lawyer. "
        "Be concise — 2-3 sentences max. Do NOT add legal advice."
        f"{lang_note}"
    )
    return _call_llm(system, f"Simplify this legal clause:\n\n\"{clause_text}\"", max_tokens=300)


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
    return _call_llm(system, user, max_tokens=800)


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
    return _call_llm(system, user, max_tokens=600)


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
    return _call_llm(system, user, max_tokens=600)


def generate_smart_summary(text: str, language: str = "en") -> str:
    """Generate an LLM-powered concise summary of the contract."""
    system = (
        "You are a legal document summarizer. Create a clear, structured summary of this contract. "
        "Include: parties involved, purpose, key terms, important dates, and notable clauses. "
        "Use bullet points. Keep it under 200 words. "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )
    return _call_llm(system, f"Summarize this legal document:\n\n{text[:6000]}", max_tokens=500)
