"""
ClauseCheck – PDF Report Generator
Generates professional PDF reports using reportlab.
"""

import io
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF export unavailable.")


# ── Colors ──
DARK_BG = HexColor("#0a0e1a") if REPORTLAB_AVAILABLE else None
BLUE = HexColor("#3b82f6") if REPORTLAB_AVAILABLE else None
PURPLE = HexColor("#8b5cf6") if REPORTLAB_AVAILABLE else None
RED = HexColor("#ef4444") if REPORTLAB_AVAILABLE else None
YELLOW = HexColor("#f59e0b") if REPORTLAB_AVAILABLE else None
GREEN = HexColor("#22c55e") if REPORTLAB_AVAILABLE else None
GRAY = HexColor("#64748b") if REPORTLAB_AVAILABLE else None
WHITE = HexColor("#f1f5f9") if REPORTLAB_AVAILABLE else None


def generate_pdf_report(result: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF report from analysis results.

    Returns:
        PDF bytes ready for download.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Install with: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=25*mm, bottomMargin=20*mm,
        leftMargin=20*mm, rightMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=22, textColor=HexColor("#1e293b"),
        spaceAfter=6, fontName="Helvetica-Bold",
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"],
        fontSize=14, textColor=HexColor("#1e40af"),
        spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#334155"),
        spaceAfter=6, leading=14, alignment=TA_JUSTIFY,
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#94a3b8"), spaceAfter=4,
    )

    elements = []

    # ── Title ──
    elements.append(Paragraph("⚖️ ClauseCheck Analysis Report", title_style))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=2, color=HexColor("#3b82f6")))
    elements.append(Spacer(1, 12))

    # ── Document Info ──
    doc_name = result.get("document_name", "Unknown")
    lang = result.get("language", "English")
    created = result.get("created_at", datetime.now().isoformat())
    risk = result.get("risk_score", 0)
    compliance = result.get("compliance_score", 0)

    info_data = [
        ["Document:", doc_name, "Language:", lang],
        ["Risk Score:", f"{risk}/100", "Compliance:", f"{compliance}/100"],
        ["Generated:", created[:19].replace("T", " "), "", ""],
    ]

    info_table = Table(info_data, colWidths=[80, 170, 80, 170])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), HexColor("#475569")),
        ("TEXTCOLOR", (2, 0), (2, -1), HexColor("#475569")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # ── Score Summary ──
    risk_color = RED if risk > 60 else (YELLOW if risk > 30 else GREEN)
    comp_color = GREEN if compliance >= 70 else (YELLOW if compliance >= 40 else RED)

    score_data = [
        ["RISK SCORE", "COMPLIANCE SCORE"],
        [f"{risk}/100", f"{compliance}/100"],
    ]
    score_table = Table(score_data, colWidths=[250, 250])
    score_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, 1), 20),
        ("TEXTCOLOR", (0, 1), (0, 1), risk_color),
        ("TEXTCOLOR", (1, 1), (1, 1), comp_color),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#e2e8f0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1, HexColor("#cbd5e1")),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 16))

    # ── Summary ──
    elements.append(Paragraph("📋 Executive Summary", heading_style))
    summary = result.get("summary", "No summary available.")
    elements.append(Paragraph(summary, body_style))

    ca = result.get("clause_analysis", {})
    explanations = ca.get("explanations", {})
    overall = explanations.get("overall_summary", "")
    if overall:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Assessment:</b> {overall}", body_style))

    # ── Risk Findings ──
    risks = ca.get("risks", [])
    if risks:
        elements.append(Paragraph(f"🔍 Risk Analysis ({len(risks)} findings)", heading_style))
        for r in risks:
            sev = r.get("severity", "medium").upper()
            sev_color = "#ef4444" if sev == "HIGH" else ("#f59e0b" if sev == "MEDIUM" else "#22c55e")
            elements.append(Paragraph(
                f'<font color="{sev_color}"><b>[{sev}]</b></font> '
                f'{r.get("risk_type", "").replace("_", " ").title()} — '
                f'{r.get("description", "")}',
                body_style
            ))
            if r.get("clause_text"):
                elements.append(Paragraph(
                    f'<i>"{r["clause_text"][:200]}..."</i>', small_style
                ))
            elements.append(Spacer(1, 4))

    # ── Compliance Checklist ──
    comp_details = ca.get("compliance", {}).get("details", [])
    if comp_details:
        elements.append(Paragraph("✅ Compliance Checklist", heading_style))
        for item in comp_details:
            check = "✓" if item.get("found") else "✗"
            color = "#22c55e" if item.get("found") else "#ef4444"
            elements.append(Paragraph(
                f'<font color="{color}"><b>{check}</b></font> '
                f'{item.get("clause_type", "").replace("_", " ").title()} — '
                f'{item.get("description", "")}',
                body_style
            ))

    # ── Obligations ──
    obligations = ca.get("obligations", [])
    if obligations:
        elements.append(Paragraph(f"📌 Key Obligations ({len(obligations)})", heading_style))
        for obl in obligations[:15]:
            strength = obl.get("strength", "").upper()
            elements.append(Paragraph(
                f'<b>[{strength}]</b> {obl.get("text", "")[:200]}', body_style
            ))

    # ── Footer ──
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cbd5e1")))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Generated by ClauseCheck — AI Legal Contract Analyzer. "
        "This report does not constitute legal advice.",
        small_style
    ))

    doc.build(elements)
    return buffer.getvalue()
