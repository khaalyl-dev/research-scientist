"""
Page Recherche — US-01 + US-07

Runs the LangGraph pipeline with:
- live per-agent progress checklist
- st.write_stream() of each agent's narrative as it completes
"""

from __future__ import annotations

import time
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from app.components.agent_progress import (
    build_agent_narrative,
    init_agent_statuses,
    progress_fraction,
    render_agent_checklist,
    stream_agent_text,
)
from src.agents.graph import PIPELINE_AGENTS, stream_pipeline

load_dotenv()

_LEVEL_TO_VALUE = {
    "Débutant": "beginner",
    "Intermédiaire": "intermediate",
    "Expert": "expert",
}

_AGENT_LABELS = {agent_id: label for agent_id, label in PIPELINE_AGENTS}


def render_recherche_page() -> None:
    st.title("🔍 Recherche")
    st.caption(
        "Pose une question — progression + streaming de la réponse "
        "agent par agent (Planner → Teacher)."
    )

    with st.form("recherche_form"):
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input(
                "Question de recherche",
                placeholder=(
                    "e.g. What are the main approaches to hallucination "
                    "mitigation in LLMs?"
                ),
            )
        with col2:
            level_label = st.selectbox(
                "Niveau",
                ["Débutant", "Intermédiaire", "Expert"],
                index=1,
            )
        submitted = st.form_submit_button("🔍 Rechercher", use_container_width=True)

    if not submitted:
        if "last_pipeline_result" in st.session_state:
            _render_saved_result(st.session_state["last_pipeline_result"])
        else:
            st.info(
                "👆 Entre une question pour lancer le pipeline multi-agents. "
                "Chaque agent streame sa sortie dès qu’il termine."
            )
        return

    if not query.strip():
        st.warning("Merci d'entrer une question avant de lancer la recherche.")
        return

    user_level = _LEVEL_TO_VALUE[level_label]
    statuses = init_agent_statuses()
    start = time.monotonic()
    agent_streams: list[dict[str, str]] = []

    progress = st.progress(0.0, text="Démarrage du pipeline…")
    checklist_box = st.empty()
    status_box = st.status("Pipeline en cours…", expanded=True)

    st.subheader("Flux agent par agent")
    stream_panel = st.container()

    final_state: dict[str, Any] | None = None
    error_message: str | None = None
    current_agent: str | None = None
    last_partial_state: dict[str, Any] | None = None

    with status_box:
        with checklist_box.container():
            render_agent_checklist(statuses)

        for event in stream_pipeline(query.strip(), user_level=user_level):
            kind = event.get("event")

            if kind == "start":
                st.write(f"Session `{event['session_id'][:8]}…`")
                continue

            if kind == "agent":
                agent = event["agent"]
                state = event.get("state") or {}
                output = event.get("output") or {}
                last_partial_state = state

                if (
                    current_agent
                    and current_agent != agent
                    and statuses.get(current_agent) == "running"
                ):
                    statuses[current_agent] = "done"

                current_agent = agent
                statuses[agent] = "running"
                with checklist_box.container():
                    render_agent_checklist(statuses, current=agent)

                label = _AGENT_LABELS.get(agent, agent)
                st.write(f"⏳ {label}")

                narrative = build_agent_narrative(agent, output, state)
                with stream_panel:
                    st.write_stream(stream_agent_text(narrative))
                    st.divider()
                agent_streams.append({"agent": agent, "text": narrative})

                statuses[agent] = "done"
                progress.progress(
                    progress_fraction(statuses),
                    text=f"Terminé : {label}",
                )
                continue

            if kind == "done":
                final_state = event.get("state") or {}
                for agent_id, _ in PIPELINE_AGENTS:
                    if statuses.get(agent_id) != "error":
                        statuses[agent_id] = "done"
                progress.progress(1.0, text="Pipeline terminé")
                status_box.update(label="Pipeline terminé", state="complete")
                continue

            if kind == "error":
                error_message = event.get("error") or "Erreur inconnue"
                last_partial_state = event.get("state")
                if current_agent:
                    statuses[current_agent] = "error"
                status_box.update(label="Pipeline en échec", state="error")
                break

    elapsed = time.monotonic() - start
    with checklist_box.container():
        render_agent_checklist(statuses)

    if error_message:
        st.error(f"Le pipeline a échoué : {error_message}")
        final_state = final_state or last_partial_state

    if not final_state:
        return

    result_payload = {
        "query": query.strip(),
        "level_label": level_label,
        "user_level": user_level,
        "elapsed": elapsed,
        "state": final_state,
        "agent_streams": agent_streams,
    }
    st.session_state["last_pipeline_result"] = result_payload
    _render_saved_result(result_payload, show_stream_replay=False)


def _render_saved_result(
    payload: dict[str, Any],
    show_stream_replay: bool = True,
) -> None:
    state = payload["state"]
    elapsed = payload.get("elapsed", 0.0)
    level_label = payload.get("level_label", "")
    agent_streams = payload.get("agent_streams") or []

    sub_queries = state.get("sub_queries") or []
    sources = state.get("sources") or []
    claims = state.get("claims") or []
    contradictions = state.get("contradictions") or []
    final_response = state.get("final_response") or ""

    st.success(
        f"Terminé en {elapsed:.1f}s — "
        f"{len(sub_queries)} sous-requêtes · {len(sources)} sources · "
        f"{len(claims)} claims · niveau {level_label}"
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sous-requêtes", len(sub_queries))
    m2.metric("Sources", len(sources))
    m3.metric("Claims", len(claims))
    m4.metric("Contradictions", len(contradictions))

    if show_stream_replay and agent_streams:
        with st.expander("📼 Revoir le flux agent par agent", expanded=False):
            for item in agent_streams:
                st.markdown(item.get("text") or "")
                st.divider()

    with st.expander(f"🧩 Sous-requêtes ({len(sub_queries)})", expanded=True):
        if not sub_queries:
            st.caption("Aucune sous-requête.")
        for i, sq in enumerate(sub_queries, 1):
            st.markdown(f"{i}. {sq}")

    with st.expander(f"📄 Sources ({len(sources)})", expanded=False):
        for src in sources:
            title = src.get("title") if isinstance(src, dict) else getattr(src, "title", "Source")
            url = src.get("url") if isinstance(src, dict) else getattr(src, "url", "")
            st.markdown(f"- **{title}** — [{url}]({url})" if url else f"- **{title}**")

    with st.expander(f"📌 Claims ({len(claims)})", expanded=False):
        for claim in claims[:20]:
            if isinstance(claim, dict):
                st.markdown(
                    f"- **{claim.get('entity', '?')}** — {claim.get('claim', '')} "
                    f"_(confiance {claim.get('confidence', 0):.2f})_"
                )
            else:
                st.write(claim)
        if len(claims) > 20:
            st.caption(f"… et {len(claims) - 20} autres")

    st.subheader("Réponse finale")
    if final_response:
        st.markdown(final_response)
    else:
        st.info("Pas encore de réponse finale (Teacher stub / pipeline incomplet).")

    if state.get("error"):
        st.warning(f"Avertissement pipeline : {state['error']}")
