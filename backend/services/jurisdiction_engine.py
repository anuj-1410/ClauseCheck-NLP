"""
ClauseCheck – Jurisdiction-Aware Compliance Engine
Adapts compliance rules and legal references based on selected jurisdiction.

Upgrades:
  - Added adjust_risk_severity() for dynamic risk severity adjustment
  - Risk severity is now jurisdiction-aware (e.g., non-compete in India → high)
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Jurisdiction Definitions
# ──────────────────────────────────────────────
JURISDICTIONS = {
    "india": {
        "name": "India",
        "laws": {
            "contract": "Indian Contract Act, 1872",
            "employment": "Industrial Disputes Act, 1947; Shops and Establishments Act",
            "it": "Information Technology Act, 2000",
            "consumer": "Consumer Protection Act, 2019",
            "arbitration": "Arbitration and Conciliation Act, 1996",
            "companies": "Companies Act, 2013",
            "ip": "Patents Act, 1970; Copyright Act, 1957; Trademarks Act, 1999",
            "privacy": "Digital Personal Data Protection Act, 2023",
        },
        "required_clauses": {
            "governing_law": {"weight": 10, "ref": "Section 73, Indian Contract Act"},
            "dispute_resolution": {"weight": 10, "ref": "Arbitration Act, 1996"},
            "termination": {"weight": 9, "ref": "Section 39-40, Indian Contract Act"},
            "liability": {"weight": 9, "ref": "Section 73-74, Indian Contract Act"},
            "confidentiality": {"weight": 8, "ref": "IT Act, Section 72A"},
            "payment_terms": {"weight": 9, "ref": "Section 56, Indian Contract Act"},
            "force_majeure": {"weight": 7, "ref": "Section 56, Doctrine of Frustration"},
            "indemnity": {"weight": 8, "ref": "Section 124-125, Indian Contract Act"},
            "notice": {"weight": 6, "ref": "General contract practice"},
            "stamp_duty": {"weight": 7, "ref": "Indian Stamp Act, 1899"},
            "non_compete": {"weight": 6, "ref": "Section 27, Indian Contract Act (void if unreasonable)"},
        },
        "risk_notes": {
            "non_compete": "Non-compete clauses are generally void under Section 27 of Indian Contract Act unless during employment.",
            "unlimited_liability": "Courts may reduce penalty under Section 74 if deemed unreasonable.",
            "exclusive_jurisdiction": "Parties can agree on jurisdiction but courts retain protective jurisdiction.",
        }
    },
    "us": {
        "name": "United States",
        "laws": {
            "contract": "Uniform Commercial Code (UCC); Restatement of Contracts",
            "employment": "Fair Labor Standards Act; National Labor Relations Act",
            "privacy": "CCPA (California); State privacy laws",
            "ip": "17 U.S.C. (Copyright); 35 U.S.C. (Patent); Lanham Act (Trademark)",
            "arbitration": "Federal Arbitration Act",
        },
        "required_clauses": {
            "governing_law": {"weight": 10, "ref": "Choice of law principles"},
            "dispute_resolution": {"weight": 9, "ref": "Federal Arbitration Act"},
            "termination": {"weight": 9, "ref": "At-will vs for-cause termination"},
            "liability": {"weight": 10, "ref": "Common law liability principles"},
            "confidentiality": {"weight": 8, "ref": "Trade Secrets Act"},
            "payment_terms": {"weight": 9, "ref": "UCC Article 2"},
            "force_majeure": {"weight": 7, "ref": "Common law impracticability"},
            "indemnity": {"weight": 9, "ref": "Common law indemnification"},
            "warranties": {"weight": 8, "ref": "UCC implied warranties"},
            "intellectual_property": {"weight": 9, "ref": "Work for hire doctrine"},
        },
        "risk_notes": {
            "non_compete": "Enforceability varies by state. California bans most non-competes.",
            "auto_renewal": "Many states require advance notice before auto-renewal (e.g., NY GBL § 527-a).",
        }
    },
    "uk": {
        "name": "United Kingdom",
        "laws": {
            "contract": "Contract Act (common law); Unfair Contract Terms Act 1977",
            "employment": "Employment Rights Act 1996; Equality Act 2010",
            "privacy": "UK GDPR; Data Protection Act 2018",
            "consumer": "Consumer Rights Act 2015",
        },
        "required_clauses": {
            "governing_law": {"weight": 10, "ref": "Rome I Regulation (retained)"},
            "dispute_resolution": {"weight": 9, "ref": "Arbitration Act 1996"},
            "termination": {"weight": 9, "ref": "Common law; Employment Rights Act"},
            "liability": {"weight": 10, "ref": "Unfair Contract Terms Act 1977"},
            "confidentiality": {"weight": 8, "ref": "Common law duty; UK GDPR"},
            "data_protection": {"weight": 9, "ref": "UK GDPR, Data Protection Act 2018"},
            "force_majeure": {"weight": 7, "ref": "Common law frustration doctrine"},
            "payment_terms": {"weight": 8, "ref": "Late Payment of Commercial Debts Act 1998"},
        },
        "risk_notes": {
            "unlimited_liability": "UCTA 1977 restricts exclusion of liability for negligence causing injury.",
            "non_compete": "Must be reasonable in scope, duration, and geography to be enforceable.",
        }
    },
    "general": {
        "name": "General / International",
        "laws": {
            "contract": "General contract law principles",
            "trade": "CISG (UN Convention on Contracts for the International Sale of Goods)",
        },
        "required_clauses": {
            "governing_law": {"weight": 10, "ref": "Essential for international contracts"},
            "dispute_resolution": {"weight": 10, "ref": "Arbitration recommended for cross-border"},
            "termination": {"weight": 9, "ref": "Standard practice"},
            "liability": {"weight": 9, "ref": "Standard practice"},
            "confidentiality": {"weight": 8, "ref": "Standard practice"},
            "payment_terms": {"weight": 9, "ref": "Standard practice"},
            "force_majeure": {"weight": 8, "ref": "ICC Force Majeure Clause 2020"},
            "indemnity": {"weight": 7, "ref": "Standard practice"},
        },
        "risk_notes": {}
    },
}

# ──────────────────────────────────────────────
# Dynamic risk severity adjustments per jurisdiction
# ──────────────────────────────────────────────
JURISDICTION_RISK_ADJUSTMENTS = {
    "india": {
        "non_compete_broad": {
            "adjusted_severity": "high",
            "reason": "Non-compete clauses are generally void under Section 27 of Indian Contract Act. High risk of unenforceability.",
        },
        "unlimited_liability": {
            "adjusted_severity": "high",
            "reason": "Courts may reduce penalty under Section 74, but unlimited liability poses significant risk.",
        },
        "exclusive_jurisdiction": {
            "adjusted_severity": "low",
            "reason": "Indian courts retain protective jurisdiction regardless of contractual clause.",
        },
        "auto_renewal": {
            "adjusted_severity": "medium",
            "reason": "Auto-renewal is generally valid but must be clearly communicated.",
        },
    },
    "us": {
        "non_compete_broad": {
            "adjusted_severity": "medium",
            "reason": "Enforceability varies by state. California bans most non-competes; other states may enforce if reasonable.",
        },
        "unlimited_liability": {
            "adjusted_severity": "high",
            "reason": "US courts may enforce unlimited liability unless unconscionable.",
        },
        "auto_renewal": {
            "adjusted_severity": "medium",
            "reason": "Many states require advance cancellation notice. Check state-specific laws.",
        },
        "waiver_of_rights": {
            "adjusted_severity": "high",
            "reason": "Broad waivers may be challenged as unconscionable but can be enforced.",
        },
    },
    "uk": {
        "non_compete_broad": {
            "adjusted_severity": "medium",
            "reason": "Must be reasonable in scope, duration, and geography to be enforceable under UK common law.",
        },
        "unlimited_liability": {
            "adjusted_severity": "high",
            "reason": "UCTA 1977 restricts exclusion of liability for negligence causing personal injury.",
        },
        "exclusive_jurisdiction": {
            "adjusted_severity": "low",
            "reason": "Generally enforceable but may be challenged under consumer protection laws.",
        },
    },
    "general": {},
}


# ──────────────────────────────────────────────
# Contract type-specific focus areas
# ──────────────────────────────────────────────
CONTRACT_TYPES = {
    "general": {"name": "General Contract", "focus": []},
    "employment": {
        "name": "Employment Contract",
        "focus": ["non_compete", "notice", "termination", "confidentiality", "benefits"],
        "extra_checks": ["probation period", "notice period", "non-compete", "non-solicitation", "benefits"]
    },
    "nda": {
        "name": "Non-Disclosure Agreement",
        "focus": ["confidentiality", "duration", "scope", "exclusions"],
        "extra_checks": ["definition of confidential info", "duration of obligation", "exclusions", "return of materials"]
    },
    "service": {
        "name": "Service Agreement",
        "focus": ["payment_terms", "deliverables", "intellectual_property", "liability"],
        "extra_checks": ["scope of work", "delivery schedule", "acceptance criteria", "IP ownership"]
    },
    "rental": {
        "name": "Rental Agreement",
        "focus": ["payment_terms", "termination", "notice", "maintenance"],
        "extra_checks": ["security deposit", "rent escalation", "maintenance responsibility", "subletting"]
    },
    "freelance": {
        "name": "Freelance/Consulting",
        "focus": ["payment_terms", "intellectual_property", "termination", "scope"],
        "extra_checks": ["deliverables", "payment schedule", "IP ownership", "independent contractor status"]
    },
}


def get_jurisdiction_rules(jurisdiction: str = "general") -> Dict[str, Any]:
    """Get compliance rules for a jurisdiction."""
    return JURISDICTIONS.get(jurisdiction.lower(), JURISDICTIONS["general"])


def get_contract_type_info(contract_type: str = "general") -> Dict[str, Any]:
    """Get contract type specific info."""
    return CONTRACT_TYPES.get(contract_type.lower(), CONTRACT_TYPES["general"])


def get_available_jurisdictions() -> List[Dict[str, str]]:
    """Return list of available jurisdictions."""
    return [{"code": k, "name": v["name"]} for k, v in JURISDICTIONS.items()]


def get_available_contract_types() -> List[Dict[str, str]]:
    """Return list of available contract types."""
    return [{"code": k, "name": v["name"]} for k, v in CONTRACT_TYPES.items()]


def get_legal_references(jurisdiction: str, risk_type: str) -> str:
    """Get applicable legal reference for a risk type within a jurisdiction."""
    j = JURISDICTIONS.get(jurisdiction.lower(), JURISDICTIONS["general"])
    return j.get("risk_notes", {}).get(risk_type, "")


def adjust_risk_severity(
    risks: List[Dict],
    jurisdiction: str = "general"
) -> List[Dict]:
    """
    Dynamically adjust risk severity based on jurisdiction context.

    For example:
      - Non-compete in India → High risk (Section 27 makes it largely void)
      - Non-compete in US → Medium risk (varies by state)
      - Non-compete in General → Keep original severity

    Adds 'jurisdiction_note' to each adjusted risk.
    """
    adjustments = JURISDICTION_RISK_ADJUSTMENTS.get(
        jurisdiction.lower(), {}
    )

    if not adjustments:
        return risks

    for risk in risks:
        risk_type = risk.get("risk_type", "")
        if risk_type in adjustments:
            adjustment = adjustments[risk_type]
            original_severity = risk.get("severity", "medium")
            new_severity = adjustment["adjusted_severity"]

            risk["original_severity"] = original_severity
            risk["severity"] = new_severity
            risk["jurisdiction_note"] = adjustment["reason"]

            # Recalculate risk score based on new severity
            risk["risk_score"] = {"high": 8, "medium": 5, "low": 2}.get(new_severity, 5)

            logger.debug(
                f"Risk '{risk_type}' severity: {original_severity} → {new_severity} "
                f"(jurisdiction: {jurisdiction})"
            )

    return risks
