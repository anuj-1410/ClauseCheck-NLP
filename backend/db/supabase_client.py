"""
ClauseCheck – Supabase Database Client
Handles connection to Supabase via REST API and CRUD operations for analysis results.
Falls back to in-memory storage if Supabase credentials are not configured.
"""

import uuid
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# In-memory fallback storage
_memory_store: List[Dict[str, Any]] = []
_MAX_MEMORY_STORE_ITEMS = 200
_LOCAL_STORE_PATH = Path(__file__).with_name("analysis_results_fallback.json")
_LOCAL_STORE_LOCK = threading.Lock()
_SUPABASE_CONNECT_TIMEOUT_SECONDS = 10.0
_SUPABASE_READ_TIMEOUT_SECONDS = 20.0
_SUPABASE_WRITE_TIMEOUT_SECONDS = 60.0
_supabase_url = ""
_supabase_key = ""
_use_supabase = False


def _headers(prefer: Optional[str] = None):
    """Build Supabase REST API headers."""
    headers = {
        "apikey": _supabase_key,
        "Authorization": f"Bearer {_supabase_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = f"return={prefer}"
    return headers


def _rest_url(table: str = "analysis_results"):
    """Build Supabase REST endpoint URL."""
    return f"{_supabase_url}/rest/v1/{table}"


def _timeout(total_seconds: float) -> httpx.Timeout:
    """Build consistent HTTP timeouts for Supabase requests."""
    return httpx.Timeout(total_seconds, connect=_SUPABASE_CONNECT_TIMEOUT_SECONDS)


def _payload_size_kb(payload: Dict[str, Any]) -> float:
    """Approximate JSON payload size to help diagnose slow inserts."""
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) / 1024


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
                timeout=_timeout(_SUPABASE_READ_TIMEOUT_SECONDS),
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
    payload_size_kb = _payload_size_kb(record)

    if _use_supabase:
        try:
            resp = httpx.post(
                _rest_url(),
                headers=_headers(prefer="minimal"),
                json=record,
                timeout=_timeout(_SUPABASE_WRITE_TIMEOUT_SECONDS),
            )
            if resp.status_code in (200, 201, 204):
                logger.info("Stored result in Supabase: %s (%.1f KB)", record["id"], payload_size_kb)
                return _normalize_record(record)
            else:
                logger.error(
                    "Supabase insert failed (%s): %s. Payload size: %.1f KB. Falling back locally.",
                    resp.status_code,
                    resp.text,
                    payload_size_kb,
                )
                _append_to_fallback_store(record)
                return _normalize_record(record)
        except Exception as e:
            logger.error(
                "Supabase insert failed: %s. Payload size: %.1f KB. Falling back locally.",
                e,
                payload_size_kb,
            )
            _append_to_fallback_store(record)
            return _normalize_record(record)
    else:
        _append_to_fallback_store(record)
        logger.info("Stored result in local fallback: %s", record["id"])
        return _normalize_record(record)


def get_all_results() -> List[Dict[str, Any]]:
    """Fetch all analysis results, newest first."""
    fallback_results = _collect_fallback_results()

    if _use_supabase:
        try:
            resp = httpx.get(
                _rest_url(),
                headers=_headers(),
                params={"select": "*", "order": "created_at.desc"},
                timeout=_timeout(_SUPABASE_READ_TIMEOUT_SECONDS),
            )
            if resp.status_code == 200:
                return _normalize_records(_merge_records(fallback_results, resp.json()))
            else:
                logger.error(f"Supabase fetch failed ({resp.status_code})")
                return _normalize_records(fallback_results)
        except Exception as e:
            logger.error(f"Supabase fetch failed: {e}. Returning fallback store.")
            return _normalize_records(fallback_results)
    else:
        return _normalize_records(fallback_results)


def get_result_by_id(result_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single analysis result by ID."""
    if _use_supabase:
        try:
            resp = httpx.get(
                _rest_url(),
                headers=_headers(),
                params={"select": "*", "id": f"eq.{result_id}"},
                timeout=_timeout(_SUPABASE_READ_TIMEOUT_SECONDS),
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return _normalize_record(data[0])
            else:
                logger.error(f"Supabase fetch failed ({resp.status_code})")
        except Exception as e:
            logger.error(f"Supabase fetch failed: {e}.")

    local_record = _find_in_local_store(result_id)
    if local_record is not None:
        return _normalize_record(local_record)

    return _find_in_memory(result_id)


def _append_to_fallback_store(record: Dict[str, Any]) -> None:
    """Persist a fallback copy locally and in memory."""
    try:
        _append_to_local_store(record)
    except Exception as exc:
        logger.error("Local fallback write failed: %s", exc)

    _append_to_memory_store(record)


def _collect_fallback_results() -> List[Dict[str, Any]]:
    """Collect locally cached results from disk and memory."""
    return _merge_records(_load_local_store(), list(_memory_store))


def _merge_records(*record_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge records by ID so remote data can override local fallbacks."""
    merged: Dict[str, Dict[str, Any]] = {}

    for records in record_groups:
        for record in records or []:
            if not isinstance(record, dict):
                continue
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                continue
            merged[record_id] = record

    return list(merged.values())


def _normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize and sort records newest first."""
    return [
        _normalize_record(record)
        for record in sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)
    ]


def _load_local_store() -> List[Dict[str, Any]]:
    """Load locally cached fallback records from disk."""
    with _LOCAL_STORE_LOCK:
        return _load_local_store_unlocked()


def _load_local_store_unlocked() -> List[Dict[str, Any]]:
    """Load locally cached fallback records from disk without acquiring the lock."""
    if not _LOCAL_STORE_PATH.exists():
        return []

    try:
        payload = json.loads(_LOCAL_STORE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read local fallback store: %s", exc)
        return []

    if not isinstance(payload, list):
        return []

    return [record for record in payload if isinstance(record, dict)]


def _append_to_local_store(record: Dict[str, Any]) -> None:
    """Append one record to the on-disk fallback store."""
    with _LOCAL_STORE_LOCK:
        records = [item for item in _load_local_store_unlocked() if item.get("id") != record.get("id")]
        records.append(record)
        if len(records) > _MAX_MEMORY_STORE_ITEMS:
            records = sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)[:_MAX_MEMORY_STORE_ITEMS]
        _LOCAL_STORE_PATH.write_text(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def _find_in_local_store(result_id: str) -> Optional[Dict[str, Any]]:
    """Find a result in the on-disk fallback store."""
    for record in _load_local_store():
        if record.get("id") == result_id:
            return record
    return None


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
    return _normalize_records(list(_memory_store))


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
