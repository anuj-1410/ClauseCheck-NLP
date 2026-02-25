"""
ClauseCheck – History Router
GET /api/history — Retrieve past analysis results.
GET /api/history/{id} — Retrieve a single result.
"""

import logging
from fastapi import APIRouter, HTTPException

from db.supabase_client import get_all_results, get_result_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def list_history():
    """Return all analysis results, newest first."""
    try:
        results = get_all_results()
        # Return lightweight summaries (without full clause_analysis)
        summaries = []
        for r in results:
            summaries.append({
                "id": r.get("id"),
                "document_name": r.get("document_name"),
                "language": r.get("language"),
                "risk_score": r.get("risk_score"),
                "compliance_score": r.get("compliance_score"),
                "summary": r.get("summary", "")[:200],
                "created_at": r.get("created_at")
            })
        return {"success": True, "count": len(summaries), "results": summaries}
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{result_id}")
async def get_history_detail(result_id: str):
    """Return a single analysis result with full clause analysis."""
    try:
        result = get_result_by_id(result_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Analysis result not found.")
        return {"success": True, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch result {result_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
