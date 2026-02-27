"""
ClauseCheck – Chat/Negotiate/What-If Router
POST /api/chat — Q&A with contract context
POST /api/negotiate — Negotiation suggestions
POST /api/whatif — What-if scenario simulation
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.llm_service import answer_question, suggest_negotiation, simulate_what_if, is_available
from db.supabase_client import get_result_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    analysis_id: str
    language: Optional[str] = "en"


class NegotiateRequest(BaseModel):
    clause_text: str
    risk_type: str
    severity: str


class WhatIfRequest(BaseModel):
    original_clause: str
    modified_clause: str
    analysis_id: Optional[str] = None


@router.post("/chat")
async def chat_with_contract(req: ChatRequest):
    """Q&A chatbot — answer questions about a specific analyzed contract."""
    if not is_available():
        raise HTTPException(status_code=503, detail="LLM service not configured. Add GROQ_API_KEY to .env")

    # Get the contract text from stored analysis
    result = get_result_by_id(req.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Build context from clause analysis
    ca = result.get("clause_analysis", {})
    clauses = ca.get("clauses", [])
    context = "\n\n".join([f"Clause {c['id']}: {c['text']}" for c in clauses])

    if not context:
        context = result.get("summary", "No contract text available.")

    answer = answer_question(req.question, context, req.language or "en")

    return {
        "success": True,
        "question": req.question,
        "answer": answer,
        "document_name": result.get("document_name", ""),
    }


@router.post("/negotiate")
async def get_negotiation_advice(req: NegotiateRequest):
    """Get negotiation suggestions for a risky clause."""
    if not is_available():
        raise HTTPException(status_code=503, detail="LLM service not configured. Add GROQ_API_KEY to .env")

    advice = suggest_negotiation(req.clause_text, req.risk_type, req.severity)

    return {
        "success": True,
        "clause_text": req.clause_text[:200],
        "advice": advice,
    }


@router.post("/whatif")
async def what_if_simulation(req: WhatIfRequest):
    """Simulate what-if scenario for clause modification."""
    if not is_available():
        raise HTTPException(status_code=503, detail="LLM service not configured. Add GROQ_API_KEY to .env")

    analysis = simulate_what_if(req.original_clause, req.modified_clause)

    return {
        "success": True,
        "original": req.original_clause[:200],
        "modified": req.modified_clause[:200],
        "analysis": analysis,
    }
