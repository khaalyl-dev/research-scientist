"""Persist pipeline results across Streamlit page navigation."""

from __future__ import annotations

import json
from typing import Any


def _to_plain(obj: Any) -> Any:
    """Convert enums / Pydantic / nested values into JSON-safe Python types."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if hasattr(obj, "model_dump"):
        return _to_plain(obj.model_dump())
    if hasattr(obj, "value") and not isinstance(obj, (str, bytes)):
        # Enum-like
        try:
            return _to_plain(obj.value)
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return str(obj)


def sanitize_pipeline_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied, JSON-roundtrippable payload for st.session_state."""
    plain = _to_plain(payload)
    # Round-trip through JSON to drop any leftover non-serializable junk
    return json.loads(json.dumps(plain, ensure_ascii=False, default=str))


RESULT_KEY = "last_pipeline_result"
SESSION_ID_KEY = "last_session_id"
CLAIMS_KEY = "last_claims"
SOURCES_KEY = "last_sources"
QUERY_KEY = "recherche_query"
LEVEL_KEY = "recherche_level"


def save_pipeline_result(st_module, payload: dict[str, Any]) -> dict[str, Any]:
    """Sanitize + store payload and graphe helper keys in session_state."""
    clean = sanitize_pipeline_payload(payload)
    st_module.session_state[RESULT_KEY] = clean

    state = clean.get("state") or {}
    session_id = state.get("session_id")
    claims = state.get("claims") or []
    sources = state.get("sources") or []

    if session_id:
        st_module.session_state[SESSION_ID_KEY] = session_id
    st_module.session_state[CLAIMS_KEY] = claims
    st_module.session_state[SOURCES_KEY] = sources
    return clean


def load_pipeline_result(st_module) -> dict[str, Any] | None:
    raw = st_module.session_state.get(RESULT_KEY)
    if not isinstance(raw, dict) or "state" not in raw:
        return None
    return raw
