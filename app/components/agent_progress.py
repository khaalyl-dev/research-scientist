"""
Shared Streamlit helpers for agent progress + streaming (US-07).
"""

from __future__ import annotations

import html
import time
from typing import Any, Iterable

import streamlit as st

from src.agents.graph import PIPELINE_AGENTS

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
    """Render a styled per-agent checklist."""
    rows: list[str] = ['<div class="ars-checklist">']
    for agent_id, label in PIPELINE_AGENTS:
        status = statuses.get(agent_id, "pending")
        if current == agent_id and status == "pending":
            status = "running"
        css = f"is-{status}" if status in {"running", "done", "error"} else ""
        short = label.split("—")[0].strip()
        suffix = "…" if status == "running" else ""
        rows.append(
            f'<div class="ars-step {css}">'
            f'<span class="ars-dot"></span>'
            f'<span class="ars-step-label">{html.escape(short)}{suffix}</span>'
            f"</div>"
        )
    rows.append("</div>")
    st.markdown("\n".join(rows), unsafe_allow_html=True)


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
        type_counts: dict[str, int] = {}
        for src in sources:
            if isinstance(src, dict):
                stype = str(src.get("source_type") or "web")
            else:
                stype = str(getattr(src, "source_type", "web"))
                if hasattr(stype, "value"):
                    stype = stype.value
            type_counts[stype] = type_counts.get(stype, 0) + 1
        if type_counts:
            breakdown = ", ".join(f"{k}×{v}" for k, v in sorted(type_counts.items()))
            lines.append(f"Répartition : `{breakdown}`\n\n")
        for src in sources[:5]:
            if isinstance(src, dict):
                name = src.get("title") or src.get("url") or "Source"
                url = src.get("url") or ""
                stype = src.get("source_type") or ""
            else:
                name = getattr(src, "title", "Source")
                url = getattr(src, "url", "")
                stype = getattr(src, "source_type", "")
                if hasattr(stype, "value"):
                    stype = stype.value
            prefix = f"`{stype}` " if stype else ""
            if url:
                lines.append(f"- {prefix}[{name}]({url})\n")
            else:
                lines.append(f"- {prefix}{name}\n")
        if len(sources) > 5:
            lines.append(f"\n_… et {len(sources) - 5} autres._\n")
        if state.get("error"):
            lines.append(f"\nNote: {state['error']}\n")
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
                claim_a = item.get("claim_a") or ""
                claim_b = item.get("claim_b") or ""
                score = item.get("similarity_score", item.get("divergence_score", "?"))
                expl = item.get("explanation") or ""
                if claim_a and claim_b:
                    lines.append(
                        f"- **A:** {claim_a}\n"
                        f"  **B:** {claim_b}\n"
                        f"  _(sim. {score})_\n"
                    )
                elif expl:
                    lines.append(f"- {expl}\n")
                else:
                    lines.append(f"- score={score}\n")
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

    return f"### {title}\n\n_Étape terminée._\n"
