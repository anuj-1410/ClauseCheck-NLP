"""
ClauseCheck – Supabase Database Client
Handles connection to Supabase via REST API and CRUD operations for analysis results.
Falls back to in-memory storage if Supabase credentials are not configured.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# In-memory fallback storage
_memory_store: List[Dict[str, Any]] = []
_MAX_MEMORY_STORE_ITEMS = 200
_supabase_url = ""
_supabase_key = ""
_use_supabase = False


def _headers():
    """Build Supabase REST API headers."""
    return {
        "apikey": _supabase_key,
        "Authorization": f"Bearer {_supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_url(table: str = "analysis_results"):
    """Build Supabase REST endpoint URL."""
    return f"{_supabase_url}/rest/v1/{table}"


def initialize(url: str, key: str):
    """Initialize Supabase connection. Falls back to memory if credentials are missing."""
    global _supabase_url, _supabase_key, _use_supabase

    if url and key and url != "https://your-project.supabase.co":
        _supabase_url = url.rstrip("/")
        _supabase_key = key

        # Test the connection
        try:
            resp = httpx.get(
                _rest_url(),
                headers=_headers(),
                params={"select": "id", "limit": "1"},
                timeout=10,
            )
            if resp.status_code in (200, 206):
                _use_supabase = True
                logger.info("Supabase connected successfully.")
            else:
                logger.warning(
                    f"Supabase responded with {resp.status_code}: {resp.text}. "
                    "Using in-memory storage."
                )
                _use_supabase = False
        except Exception as e:
            logger.warning(f"Failed to connect to Supabase: {e}. Using in-memory storage.")
            _use_supabase = False
    else:
        logger.info("Supabase credentials not configured. Using in-memory storage.")
        _use_supabase = False


def store_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store an analysis result.

    Args:
        data: Analysis result containing document_name, language,
              risk_score, compliance_score, summary, clause_analysis

    Returns:
        The stored record with generated id and timestamp.
    """
    record = {
        "id": str(uuid.uuid4()),
        "document_name": data.get("document_name", "Unknown"),
        "language": data.get("language", "en"),
        "risk_score": data.get("risk_score", 0),
        "compliance_score": data.get("compliance_score", 0),
        "summary": data.get("summary", ""),
        "clause_analysis": data.get("clause_analysis", {}),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    if _use_supabase:
        try:
            resp = httpx.post(
                _rest_url(),
                headers=_headers(),
                json=record,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Stored result in Supabase: {record['id']}")
                returned = resp.json()
                stored = returned[0] if isinstance(returned, list) and returned else record
                return _normalize_record(stored)
            else:
                logger.error(f"Supabase insert failed ({resp.status_code}): {resp.text}")
                _append_to_memory_store(record)
                return _normalize_record(record)
        except Exception as e:
            logger.error(f"Supabase insert failed: {e}. Falling back to memory.")
            _append_to_memory_store(record)
            return _normalize_record(record)
    else:
        _append_to_memory_store(record)
        logger.info(f"Stored result in memory: {record['id']}")
        return _normalize_record(record)


def get_all_results() -> List[Dict[str, Any]]:
    """Fetch all analysis results, newest first."""
    if _use_supabase:
        try:
            resp = httpx.get(
                _rest_url(),
                headers=_headers(),
                params={"select": "*", "order": "created_at.desc"},
                timeout=10,
            )
            if resp.status_code == 200:
                return [_normalize_record(record) for record in resp.json()]
            else:
                logger.error(f"Supabase fetch failed ({resp.status_code})")
                return _get_normalized_memory_store()
        except Exception as e:
            logger.error(f"Supabase fetch failed: {e}. Returning memory store.")
            return _get_normalized_memory_store()
    else:
        return _get_normalized_memory_store()


def get_result_by_id(result_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single analysis result by ID."""
    if _use_supabase:
        try:
            resp = httpx.get(
                _rest_url(),
                headers=_headers(),
                params={"select": "*", "id": f"eq.{result_id}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return _normalize_record(data[0]) if data else None
            else:
                logger.error(f"Supabase fetch failed ({resp.status_code})")
                return _find_in_memory(result_id)
        except Exception as e:
            logger.error(f"Supabase fetch failed: {e}.")
            return _find_in_memory(result_id)
    else:
        return _find_in_memory(result_id)


def _find_in_memory(result_id: str) -> Optional[Dict[str, Any]]:
    """Find a result in the in-memory store."""
    for record in _memory_store:
        if record["id"] == result_id:
            return _normalize_record(record)
    return None


def _append_to_memory_store(record: Dict[str, Any]) -> None:
    """Store a record in memory with a bounded history to avoid unbounded RAM growth."""
    _memory_store.append(record)
    overflow = len(_memory_store) - _MAX_MEMORY_STORE_ITEMS
    if overflow > 0:
        del _memory_store[:overflow]
        logger.warning("In-memory store limit reached. Evicted %s old result(s).", overflow)


def _get_normalized_memory_store() -> List[Dict[str, Any]]:
    """Return normalized in-memory records, newest first."""
    return [
        _normalize_record(record)
        for record in sorted(_memory_store, key=lambda x: x["created_at"], reverse=True)
    ]


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize stored results so callers always get a consistent shape."""
    normalized = dict(record)
    clause_analysis = normalized.get("clause_analysis", {})

    if isinstance(clause_analysis, str):
        try:
            clause_analysis = json.loads(clause_analysis)
        except Exception:
            clause_analysis = {}

    if not isinstance(clause_analysis, dict):
        clause_analysis = {}

    normalized["clause_analysis"] = clause_analysis
    normalized["document_language"] = normalized.get("document_language") or normalized.get("language", "Unknown")
    normalized["display_language"] = normalized.get("display_language") or normalized["document_language"]
    normalized["extracted_images"] = normalized.get("extracted_images") or clause_analysis.get("extracted_images", [])

    return normalized
