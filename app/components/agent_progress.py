"""
Shared Streamlit helpers for agent progress + streaming (US-07).
"""

from __future__ import annotations

import time
from typing import Any, Iterable

import streamlit as st

from src.agents.graph import PIPELINE_AGENTS

_STATUS_ICON = {
    "pending": "⬜",
    "running": "⏳",
    "done": "✅",
    "error": "❌",
    "skipped": "➖",
}

_AGENT_TITLES = {
    "planner": "Planner",
    "researcher": "Researcher",
    "extractor": "Extractor",
    "fact_checker": "FactChecker",
    "reasoner": "Reasoning",
    "teacher": "Teacher",
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


def stream_words(text: str, delay_s: float = 0.012) -> Iterable[str]:
    """Yield words for st.write_stream (prose-friendly)."""
    if not text:
        return
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield chunk
        time.sleep(delay_s)


def stream_lines(text: str, delay_s: float = 0.025) -> Iterable[str]:
    """Yield lines for st.write_stream (keeps markdown lists intact)."""
    if not text:
        return
    # Preserve trailing newlines so markdown blocks render cleanly.
    parts = text.splitlines(keepends=True)
    if not parts:
        yield text
        return
    for part in parts:
        yield part
        time.sleep(delay_s)


def stream_agent_text(text: str) -> Iterable[str]:
    """Pick line-streaming for structured agent notes, words for long prose."""
    if not text:
        return
    newline_ratio = text.count("\n") / max(len(text), 1)
    if text.lstrip().startswith("#") or newline_ratio > 0.02 or text.count("\n") >= 2:
        yield from stream_lines(text)
    else:
        yield from stream_words(text)


def build_agent_narrative(
    agent: str,
    output: dict[str, Any] | None,
    state: dict[str, Any] | None,
) -> str:
    """Markdown blurb streamed when an agent finishes (US-07 agent-by-agent)."""
    output = output or {}
    state = state or {}
    title = _AGENT_TITLES.get(agent, agent.replace("_", " ").title())

    if agent == "planner":
        sub_queries = state.get("sub_queries") or []
        source_types = state.get("source_types") or []
        lines = [f"### {title}\n", "Décomposition en sous-requêtes :\n\n"]
        if not sub_queries:
            lines.append("_Aucune sous-requête._\n")
        else:
            for i, sq in enumerate(sub_queries, 1):
                lines.append(f"{i}. {sq}\n")
        if source_types:
            lines.append(f"\nSources privilégiées : `{', '.join(source_types)}`\n")
        return "".join(lines)

    if agent == "researcher":
        sources = state.get("sources") or []
        lines = [f"### {title}\n", f"**{len(sources)}** source(s) récupérée(s).\n\n"]
        for src in sources[:5]:
            if isinstance(src, dict):
                name = src.get("title") or src.get("url") or "Source"
                url = src.get("url") or ""
            else:
                name = getattr(src, "title", "Source")
                url = getattr(src, "url", "")
            if url:
                lines.append(f"- [{name}]({url})\n")
            else:
                lines.append(f"- {name}\n")
        if len(sources) > 5:
            lines.append(f"\n_… et {len(sources) - 5} autres._\n")
        if state.get("error"):
            lines.append(f"\n⚠️ {state['error']}\n")
        return "".join(lines)

    if agent == "extractor":
        batch = output.get("claims") or []
        total = state.get("claims") or []
        lines = [
            f"### {title}\n",
            f"+**{len(batch)}** claim(s) sur cette source — "
            f"total cumulé **{len(total)}**.\n\n",
        ]
        for claim in batch[:4]:
            if isinstance(claim, dict):
                entity = claim.get("entity", "?")
                text = claim.get("claim", "")
                conf = claim.get("confidence", 0)
                lines.append(f"- **{entity}** — {text} _(conf. {conf:.2f})_\n")
        if len(batch) > 4:
            lines.append(f"\n_… et {len(batch) - 4} autres dans ce lot._\n")
        return "".join(lines)

    if agent == "fact_checker":
        contradictions = state.get("contradictions") or []
        has_c = bool(state.get("has_contradictions"))
        lines = [
            f"### {title}\n",
            f"Contradictions détectées : **{len(contradictions)}**"
            f"{' (signalées)' if has_c else ''}.\n\n",
        ]
        for item in contradictions[:5]:
            if isinstance(item, dict):
                expl = item.get("explanation") or (
                    f"divergence={item.get('divergence_score', '?')}"
                )
                lines.append(f"- {expl}\n")
            else:
                lines.append(f"- {item}\n")
        if not contradictions:
            lines.append("_Aucun désaccord flagrant pour l’instant._\n")
        return "".join(lines)

    if agent == "reasoner":
        reasoning = (state.get("reasoning") or output.get("reasoning") or "").strip()
        lines = [f"### {title}\n"]
        if reasoning:
            lines.append(f"{reasoning}\n")
        else:
            lines.append("_Synthèse vide._\n")
        return "".join(lines)

    if agent == "teacher":
        response = (state.get("final_response") or output.get("final_response") or "").strip()
        lines = [f"### {title}\n", "Réponse personnalisée :\n\n"]
        if response:
            lines.append(f"{response}\n")
        else:
            lines.append("_Pas de réponse finale._\n")
        return "".join(lines)

    # Unknown / future agents
    return f"### {title}\n\n_Étape terminée._\n"
