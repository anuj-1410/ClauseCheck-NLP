"""
ClauseCheck – Report Router
GET /api/report/{id} — Generate and download PDF report.
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from db.supabase_client import get_result_by_id
from services.report_generator import generate_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{result_id}")
async def download_report(result_id: str):
    """Generate and download a PDF report for an analysis."""
    try:
        result = get_result_by_id(result_id)
        if not result:
            raise HTTPException(404, "Analysis result not found.")

        pdf_bytes = generate_pdf_report(result)

        doc_name = result.get("document_name", "report").replace(" ", "_")
        filename = f"ClauseCheck_Report_{doc_name}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(500, f"Report generation failed: {str(e)}")
