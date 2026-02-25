"""
ClauseCheck – Explanation Generation Service
Generates human-readable explanations for risk and compliance findings.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Explanation templates for risk types
# ──────────────────────────────────────────────
RISK_EXPLANATIONS = {
    "unlimited_liability": {
        "en": (
            "⚠️ This clause exposes a party to unlimited financial liability. "
            "Without a cap on damages, one party could be held responsible for "
            "an unreasonable amount. Consider negotiating a liability cap."
        ),
        "hi": (
            "⚠️ यह खंड एक पक्ष को असीमित वित्तीय दायित्व के लिए उजागर करता है। "
            "क्षति पर सीमा के बिना, एक पक्ष को अनुचित राशि के लिए जिम्मेदार ठहराया जा सकता है।"
        )
    },
    "one_sided_termination": {
        "en": (
            "⚠️ This clause allows one party to terminate the contract without "
            "cause or with minimal notice. This creates an imbalanced agreement "
            "where one party holds significantly more power."
        ),
        "hi": (
            "⚠️ यह खंड एक पक्ष को बिना कारण या न्यूनतम सूचना के अनुबंध समाप्त "
            "करने की अनुमति देता है।"
        )
    },
    "missing_notice_period": {
        "en": (
            "⚠️ No notice period is specified for termination. This means the "
            "contract could be ended abruptly without adequate preparation time."
        ),
        "hi": (
            "⚠️ समाप्ति के लिए कोई सूचना अवधि निर्दिष्ट नहीं है।"
        )
    },
    "auto_renewal": {
        "en": (
            "⚡ This contract contains an auto-renewal clause. If not actively "
            "cancelled before the renewal date, the contract will automatically "
            "extend. Ensure you track renewal dates."
        ),
        "hi": (
            "⚡ इस अनुबंध में स्वतः नवीनीकरण खंड है। यदि नवीनीकरण तिथि से "
            "पहले सक्रिय रूप से रद्द नहीं किया जाता है, तो अनुबंध स्वचालित रूप "
            "से विस्तारित होगा।"
        )
    },
    "vague_penalties": {
        "en": (
            "⚡ The penalty terms in this clause are vague or undefined. Without "
            "specific amounts or calculation methods, penalties could be disputed "
            "or set arbitrarily."
        ),
        "hi": (
            "⚡ इस खंड में दंड की शर्तें अस्पष्ट या अपरिभाषित हैं।"
        )
    },
    "non_compete_broad": {
        "en": (
            "⚡ A broad non-compete clause has been detected. This may restrict "
            "future employment or business activities significantly. Review the "
            "scope, duration, and geographic limitations."
        ),
        "hi": (
            "⚡ एक व्यापक गैर-प्रतिस्पर्धा खंड पाया गया है।"
        )
    },
    "waiver_of_rights": {
        "en": (
            "⚠️ This clause involves a waiver of significant rights. Once waived, "
            "these rights may not be recoverable. Carefully review what rights are "
            "being given up."
        ),
        "hi": (
            "⚠️ इस खंड में महत्वपूर्ण अधिकारों की छूट शामिल है।"
        )
    },
    "exclusive_jurisdiction": {
        "en": (
            "ℹ️ This clause specifies exclusive jurisdiction in a particular court. "
            "This means any disputes must be resolved in that specific location, "
            "which could be inconvenient or costly."
        ),
        "hi": (
            "ℹ️ यह खंड किसी विशेष न्यायालय में विशेष क्षेत्राधिकार निर्दिष्ट करता है।"
        )
    },
    "indemnification_broad": {
        "en": (
            "⚠️ This clause contains broad indemnification language that could "
            "expose a party to unlimited financial obligations arising from "
            "third-party claims."
        ),
        "hi": (
            "⚠️ इस खंड में व्यापक क्षतिपूर्ति भाषा है।"
        )
    },
    "confidentiality_perpetual": {
        "en": (
            "⚡ Confidentiality obligations extend indefinitely. Consider whether "
            "a reasonable time limit would be more appropriate."
        ),
        "hi": (
            "⚡ गोपनीयता दायित्व अनिश्चित काल तक बढ़ते हैं।"
        )
    },
}

# Missing clause explanations
MISSING_CLAUSE_EXPLANATIONS = {
    "termination": {
        "en": "❌ No termination clause found. The contract doesn't specify how it can be ended.",
        "hi": "❌ कोई समाप्ति खंड नहीं मिला।"
    },
    "liability": {
        "en": "❌ No liability clause found. Liability limits are not defined, which could be risky.",
        "hi": "❌ कोई दायित्व खंड नहीं मिला।"
    },
    "indemnity": {
        "en": "❌ No indemnity clause found. There's no protection against third-party claims.",
        "hi": "❌ कोई क्षतिपूर्ति खंड नहीं मिला।"
    },
    "confidentiality": {
        "en": "❌ No confidentiality clause found. Sensitive information may not be protected.",
        "hi": "❌ कोई गोपनीयता खंड नहीं मिला।"
    },
    "governing_law": {
        "en": "❌ No governing law clause found. Legal jurisdiction is undefined.",
        "hi": "❌ कोई शासी कानून खंड नहीं मिला।"
    },
    "dispute_resolution": {
        "en": "❌ No dispute resolution clause found. How disputes will be handled is unclear.",
        "hi": "❌ कोई विवाद समाधान खंड नहीं मिला।"
    },
    "force_majeure": {
        "en": "⚠️ No force majeure clause found. The contract doesn't address unforeseeable events.",
        "hi": "⚠️ कोई अप्रत्याशित घटना खंड नहीं मिला।"
    },
    "payment_terms": {
        "en": "❌ No payment terms found. Financial obligations are not clearly defined.",
        "hi": "❌ कोई भुगतान शर्तें नहीं मिलीं।"
    },
    "notice": {
        "en": "⚠️ No notice clause found. Formal communication procedures are undefined.",
        "hi": "⚠️ कोई सूचना खंड नहीं मिला।"
    },
    "amendment": {
        "en": "⚠️ No amendment clause found. It's unclear how the contract can be modified.",
        "hi": "⚠️ कोई संशोधन खंड नहीं मिला।"
    },
    "intellectual_property": {
        "en": "⚠️ No IP clause found. Intellectual property ownership is undefined.",
        "hi": "⚠️ कोई बौद्धिक संपदा खंड नहीं मिला।"
    },
    "warranties": {
        "en": "⚠️ No warranties clause found. No quality or accuracy guarantees are specified.",
        "hi": "⚠️ कोई वारंटी खंड नहीं मिला।"
    },
}


def generate_explanations(
    risks: List[Dict],
    compliance: Dict[str, Any],
    language: str = "en"
) -> Dict[str, Any]:
    """
    Generate human-readable explanations for all findings.

    Returns:
        Dict with:
        - risk_explanations: per-risk explanations
        - compliance_explanations: per-missing-clause explanations
        - overall_summary: high-level assessment
    """
    lang = language if language in ("en", "hi") else "en"

    # Risk explanations
    risk_explanations = []
    for risk in risks:
        risk_type = risk["risk_type"]
        template = RISK_EXPLANATIONS.get(risk_type, {})
        explanation = template.get(lang, risk.get("description", "Risk detected."))

        risk_explanations.append({
            "clause_id": risk["clause_id"],
            "risk_type": risk_type,
            "severity": risk["severity"],
            "explanation": explanation,
            "flagged_text": risk.get("matched_text", ""),
            "clause_excerpt": risk.get("clause_text", "")[:200]
        })

    # Compliance explanations
    compliance_explanations = []
    for missing in compliance.get("missing_clauses", []):
        clause_type = missing["clause_type"]
        template = MISSING_CLAUSE_EXPLANATIONS.get(clause_type, {})
        explanation = template.get(lang, f"Missing: {clause_type}")

        compliance_explanations.append({
            "clause_type": clause_type,
            "importance": missing.get("importance", "recommended"),
            "explanation": explanation
        })

    # Overall summary
    overall = _generate_overall_summary(risks, compliance, lang)

    return {
        "risk_explanations": risk_explanations,
        "compliance_explanations": compliance_explanations,
        "overall_summary": overall
    }


def _generate_overall_summary(
    risks: List[Dict],
    compliance: Dict[str, Any],
    lang: str
) -> str:
    """Generate an overall assessment summary."""
    risk_count = len(risks)
    high_risks = sum(1 for r in risks if r["severity"] == "high")
    missing_count = compliance.get("total_missing", 0)
    compliance_score = compliance.get("compliance_score", 0)

    if lang == "hi":
        if high_risks > 0:
            return (
                f"⚠️ इस अनुबंध में {risk_count} जोखिम पाए गए, "
                f"जिनमें {high_risks} उच्च गंभीरता के हैं। "
                f"अनुपालन स्कोर: {compliance_score}/100। "
                f"{missing_count} आवश्यक खंड गायब हैं।"
            )
        elif risk_count > 0:
            return (
                f"⚡ इस अनुबंध में {risk_count} मध्यम/निम्न जोखिम पाए गए। "
                f"अनुपालन स्कोर: {compliance_score}/100।"
            )
        else:
            return f"✅ कोई महत्वपूर्ण जोखिम नहीं पाए गए। अनुपालन स्कोर: {compliance_score}/100।"
    else:
        if high_risks > 0:
            return (
                f"⚠️ This contract contains {risk_count} risk finding(s), "
                f"including {high_risks} high-severity issue(s). "
                f"Compliance score: {compliance_score}/100. "
                f"{missing_count} essential clause(s) are missing. "
                f"Careful review is strongly recommended before signing."
            )
        elif risk_count > 0:
            return (
                f"⚡ This contract has {risk_count} medium/low risk finding(s). "
                f"Compliance score: {compliance_score}/100. "
                f"Review the flagged clauses before proceeding."
            )
        else:
            return (
                f"✅ No significant risks detected. "
                f"Compliance score: {compliance_score}/100. "
                f"The contract appears to be generally well-structured."
            )
