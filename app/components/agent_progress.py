"""
Shared Streamlit helpers for agent progress (US-07).
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from src.agents.graph import PIPELINE_AGENTS

_STATUS_ICON = {
    "pending": "⬜",
    "running": "⏳",
    "done": "✅",
    "error": "❌",
    "skipped": "➖",
}


def init_agent_statuses() -> dict[str, str]:
    return {agent_id: "pending" for agent_id, _ in PIPELINE_AGENTS}


def render_agent_checklist(statuses: dict[str, str], current: str | None = None) -> None:
    """Render the per-agent checklist used on the Recherche page."""
    lines: list[str] = []
    for agent_id, label in PIPELINE_AGENTS:
        status = statuses.get(agent_id, "pending")
        if current == agent_id and status == "pending":
            status = "running"
        icon = _STATUS_ICON.get(status, "⬜")
        suffix = "…" if status == "running" else ""
        lines.append(f"{icon} **{label}**{suffix}")
    st.markdown("\n\n".join(lines))


def progress_fraction(statuses: dict[str, str]) -> float:
    done = sum(1 for s in statuses.values() if s in ("done", "skipped"))
    total = max(len(PIPELINE_AGENTS), 1)
    return done / total


def stream_words(text: str, delay_s: float = 0.015) -> Iterable[str]:
    """Yield words for st.write_stream (US-07 progressive display)."""
    import time

    if not text:
        return
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield chunk
        time.sleep(delay_s)
