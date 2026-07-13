"""
Page Recherche — US-01 + US-07

Runs the LangGraph pipeline with:
- live per-agent progress checklist
- st.write_stream() of each agent's narrative as it completes
"""

from __future__ import annotations

import html
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
from app.components.theme import inject_theme
from src.agents.graph import PIPELINE_AGENTS, stream_pipeline

load_dotenv()

_LEVEL_TO_VALUE = {
    "Débutant": "beginner",
    "Intermédiaire": "intermediate",
    "Expert": "expert",
}

_AGENT_LABELS = {agent_id: label for agent_id, label in PIPELINE_AGENTS}


def _llm_status_message() -> str | None:
    """Return a user-facing warning if no LLM backend looks usable."""
    import os

    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if key.startswith("xai-"):
        return (
            "Your `.env` has an **xAI / Grok** key (`xai-...`), but this app uses "
            "**Groq** (`https://console.groq.com`). Create a Groq key that starts with "
            "`gsk_`, put it in `GROQ_API_KEY`, then restart Streamlit."
        )
    if key and not key.startswith("gsk_"):
        return (
            "`GROQ_API_KEY` does not look like a Groq key (expected prefix `gsk_`). "
            "Get one at https://console.groq.com — not xAI/Grok."
        )
    if key:
        return None
    fallback = os.getenv("GROQ_FALLBACK", "ollama") == "ollama"
    if fallback:
        return (
            "`GROQ_API_KEY` is empty in `.env`, and Ollama will be used as fallback. "
            "If Ollama is not running (`ollama serve`), Planner/Extractor will degrade "
            "(heuristic sub-queries, 0 claims)."
        )
    return (
        "`GROQ_API_KEY` is empty and Ollama fallback is disabled. "
        "Set the key in `.env` and restart Streamlit."
    )


def render_recherche_page() -> None:
    inject_theme()

    st.markdown(
        """
<div class="ars-hero">
  <div class="ars-kicker">Pipeline multi-agents</div>
  <h1 class="ars-brand">Recherche</h1>
  <p class="ars-lead">
    Pose une question — progression live et streaming agent par agent,
    du Planner au Teacher.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    llm_warn = _llm_status_message()
    if llm_warn:
        st.warning(llm_warn)

    st.markdown(
        """
<div class="ars-panel" style="margin-top:1.25rem;">
  <h3 class="ars-panel-title">Nouvelle investigation</h3>
  <p class="ars-muted">Formule ta question et choisis le niveau de réponse.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.form("recherche_form"):
        col1, col2 = st.columns([3.4, 1.1], gap="medium")
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
        submitted = st.form_submit_button("Lancer la recherche", use_container_width=True)

    if not submitted:
        if "last_pipeline_result" in st.session_state:
            _render_saved_result(st.session_state["last_pipeline_result"])
        else:
            st.markdown(
                """
<div class="ars-panel">
  <h3 class="ars-panel-title">Prêt quand tu l’es</h3>
  <p class="ars-muted" style="margin:0;">
    Entre une question pour lancer le pipeline. Chaque agent streame
    sa sortie dès qu’il termine.
  </p>
</div>
""",
                unsafe_allow_html=True,
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
    checklist_col, live_col = st.columns([1, 1.55], gap="large")

    with checklist_col:
        st.markdown("##### Agents")
        checklist_box = st.empty()

    with live_col:
        st.markdown("##### Journal live")
        status_box = st.status("Pipeline en cours…", expanded=True)

    st.markdown("##### Flux agent par agent")
    st.caption("Chaque bloc apparaît dès qu’un agent termine.")
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
                sid = str(event.get("session_id", ""))[:8]
                st.caption(f"Session `{sid}…`")
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
                short = label.split("—")[0].strip()
                st.write(f"En cours — **{short}**")

                narrative = build_agent_narrative(agent, output, state)
                with stream_panel:
                    st.markdown(
                        f'<div class="ars-stream-block">'
                        f'<div class="ars-kicker" style="margin-bottom:0.4rem;">'
                        f"{html.escape(short)}</div>",
                        unsafe_allow_html=True,
                    )
                    st.write_stream(stream_agent_text(narrative))
                    st.markdown("</div>", unsafe_allow_html=True)
                agent_streams.append({"agent": agent, "text": narrative})

                statuses[agent] = "done"
                progress.progress(
                    progress_fraction(statuses),
                    text=f"Terminé : {short}",
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
    query = payload.get("query", "")

    sub_queries = state.get("sub_queries") or []
    sources = state.get("sources") or []
    claims = state.get("claims") or []
    contradictions = state.get("contradictions") or []
    final_response = state.get("final_response") or ""

    q_safe = html.escape(query) if query else ""
    st.markdown(
        f"""
<div class="ars-panel" style="margin-top:1.2rem;">
  <h3 class="ars-panel-title">Résultats</h3>
  <p class="ars-muted" style="margin:0;">
    Terminé en <strong>{elapsed:.1f}s</strong>
    {" · " + q_safe if q_safe else ""}
    · niveau {html.escape(str(level_label))}
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ars-metric-row">', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sous-requêtes", len(sub_queries))
    m2.metric("Sources", len(sources))
    m3.metric("Claims", len(claims))
    m4.metric("Contradictions", len(contradictions))
    st.markdown("</div>", unsafe_allow_html=True)

    if show_stream_replay and agent_streams:
        with st.expander("Revoir le flux agent par agent", expanded=False):
            for item in agent_streams:
                st.markdown(item.get("text") or "")
                st.divider()

    with st.expander(f"Sous-requêtes ({len(sub_queries)})", expanded=True):
        if not sub_queries:
            st.caption("Aucune sous-requête.")
        for i, sq in enumerate(sub_queries, 1):
            st.markdown(f"{i}. {sq}")

    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for src in sources:
            title = src.get("title") if isinstance(src, dict) else getattr(src, "title", "Source")
            url = src.get("url") if isinstance(src, dict) else getattr(src, "url", "")
            st.markdown(f"- **{title}** — [{url}]({url})" if url else f"- **{title}**")

    with st.expander(f"Claims ({len(claims)})", expanded=False):
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

    st.markdown(
        """
<div class="ars-answer">
  <div class="ars-kicker">Teacher</div>
  <h3 class="ars-panel-title" style="margin-bottom:0.65rem;">Réponse finale</h3>
</div>
""",
        unsafe_allow_html=True,
    )
    if final_response:
        st.markdown(final_response)
    else:
        st.info("Pas encore de réponse finale (Teacher stub / pipeline incomplet).")

    if state.get("error"):
        st.warning(f"Avertissement pipeline : {state['error']}")

    if len(claims) == 0 and len(sources) > 0:
        st.info(
            "0 claims extraits alors que des sources existent — en général le LLM "
            "était indisponible (GROQ_API_KEY vide et/ou Ollama arrêté). "
            "Remplis `.env` puis relance Streamlit, ou démarre `ollama serve`."
        )
