"""Tests for JSON-safe session persistence helpers."""

from app.components.session_store import sanitize_pipeline_payload


def test_sanitize_strips_enums_and_nested():
    class FakeEnum:
        value = "intermediate"

    payload = {
        "query": "RAG?",
        "level_label": "Intermédiaire",
        "user_level": FakeEnum(),
        "elapsed": 12.5,
        "state": {
            "session_id": "abc",
            "user_level": FakeEnum(),
            "claims": [{"entity": "RAG", "claim": "x", "confidence": 0.9}],
            "sources": [],
            "contradictions": [],
        },
        "agent_streams": [{"agent": "planner", "text": "hi"}],
    }
    clean = sanitize_pipeline_payload(payload)
    assert clean["user_level"] == "intermediate"
    assert clean["state"]["user_level"] == "intermediate"
    assert clean["state"]["claims"][0]["entity"] == "RAG"
    # Must be JSON-serializable
    import json

    json.dumps(clean)
