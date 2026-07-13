"""
LangGraph graph builder for the agent pipeline.
"""

import uuid
from typing import List

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from src.agents.extractor import extractor_node
from src.agents.planner import planner_node
from src.agents.researcher import researcher_node
from src.agents.state import GraphState
from src.db.crud import create_session
from src.schemas.common import SessionStatus, UserLevel
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# AGENTS (stubs remain for FactChecker / Reasoning / Teacher)
# ============================================================================


async def researcher_agent(state: GraphState) -> dict:
    """Real Researcher — arXiv + web in parallel; sources stored as dicts."""
    result = await researcher_node(state)
    sources = result.get("sources") or []
    result["sources"] = [
        s.model_dump() if hasattr(s, "model_dump") else s for s in sources
    ]
    logger.info(
        f"Researcher returned {len(result['sources'])} source(s) "
        f"for {len(state.get('sub_queries') or [])} sub-quer(y/ies)"
    )
    return result


def _sync_researcher_agent(state: GraphState) -> dict:
    """Sync entrypoint for LangGraph `invoke()` (Streamlit is sync)."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(researcher_agent(state))
    # Already inside an event loop (e.g. ainvoke/astream) — run coroutine there.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, researcher_agent(state)).result()


def create_extraction_jobs(state: GraphState) -> List[Send] | str:
    """Fan-out: one parallel Extractor `Send()` per source (US-04).

    Returns:
      - ``list[Send]`` targeting ``extractor`` when sources exist
      - ``\"fact_checker\"`` when there are zero sources (skip extraction
        so the graph does not stall on an empty fan-out)
    """
    raw_sources = state.get("sources") or []
    sources: list[dict] = []
    for src in raw_sources:
        if isinstance(src, dict):
            sources.append(src)
        elif hasattr(src, "model_dump"):
            sources.append(src.model_dump())
        else:
            logger.warning(f"Skipping non-dict source in Send() fan-out: {type(src)!r}")

    if not sources:
        logger.info("No sources to extract — routing researcher → fact_checker")
        return "fact_checker"

    session_id = state.get("session_id")
    jobs = [
        Send("extractor", {"source": source, "session_id": session_id})
        for source in sources
    ]
    logger.info(f"Dispatching {len(jobs)} parallel Extractor Send() job(s)")
    return jobs


# Alias used in Extractor docs / older call sites
dispatch_to_extractors = create_extraction_jobs


def fact_checker_agent(state: GraphState) -> dict:
    """Stub FactChecker - detects contradictions."""
    print(f"[FactChecker] Checking {len(state.get('claims', []))} claims")
    return {
        "contradictions": [],
        "has_contradictions": False,
        "current_agent": "fact_checker",
    }


def reasoning_agent(state: GraphState) -> dict:
    """Stub Reasoning - synthesizes answer plan."""
    print(f"[Reasoning] Synthesizing for: {state['query']}")
    return {
        "reasoning": f"Stub reasoning for '{state['query']}'.",
        "current_agent": "reasoning",
    }


def teacher_agent(state: GraphState) -> dict:
    """Stub Teacher - writes final response."""
    level = (
        state["user_level"].value if hasattr(state["user_level"], "value") else state["user_level"]
    )
    print(f"[Teacher] Writing response at {level} level")

    return {
        "final_response": (
            f"# Answer about '{state['query']}'\n\n"
            f"**Level: {level}**\n\n"
            f"This is a stub response."
        ),
        "current_agent": "teacher",
        "status": SessionStatus.completed.value,
    }


# ============================================================================
# GRAPH BUILDER
# ============================================================================


def build_graph():
    """Build the LangGraph pipeline with parallel Extractor fan-out."""
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", _sync_researcher_agent)
    builder.add_node("extractor", extractor_node)
    builder.add_node("fact_checker", fact_checker_agent)
    builder.add_node("reasoner", reasoning_agent)
    builder.add_node("teacher", teacher_agent)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")

    # Map-reduce: Researcher → N× Extractor (Send) → FactChecker
    # Path map must list every possible destination (extractor OR fact_checker
    # when the source list is empty).
    builder.add_conditional_edges(
        "researcher",
        create_extraction_jobs,
        ["extractor", "fact_checker"],
    )

    builder.add_edge("extractor", "fact_checker")
    builder.add_edge("fact_checker", "reasoner")
    builder.add_edge("reasoner", "teacher")
    builder.add_edge("teacher", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# Ordered steps shown in the Streamlit Recherche progress UI (US-07).
PIPELINE_AGENTS: list[tuple[str, str]] = [
    ("planner", "Planner — décomposition en sous-requêtes"),
    ("researcher", "Researcher — recherche de sources"),
    ("extractor", "Extractor — extraction des claims"),
    ("fact_checker", "FactChecker — détection de contradictions"),
    ("reasoner", "Reasoning — synthèse"),
    ("teacher", "Teacher — réponse personnalisée"),
]


def _build_initial_state(query: str, user_level: str, session_id: str) -> GraphState:
    return {
        "query": query,
        "user_level": UserLevel(user_level),
        "session_id": session_id,
        "status": SessionStatus.running.value,
        "current_agent": "start",
        "retry_count": 0,
        "sub_queries": [],
        "source_types": [],
        "sources": [],
        "claims": [],
        "contradictions": [],
        "has_contradictions": False,
        "reasoning": "",
        "final_response": "",
        "error": None,
    }


def run_pipeline(query: str, user_level: str = "intermediate") -> dict:
    """Run the full agent pipeline (blocking)."""
    session_id = str(uuid.uuid4())
    try:
        create_session(session_id, query, user_level)
    except Exception as e:
        logger.warning(f"Failed to create session in database: {e}")

    graph = build_graph()
    config = {"configurable": {"thread_id": session_id}}
    return graph.invoke(_build_initial_state(query, user_level, session_id), config)


def stream_pipeline(query: str, user_level: str = "intermediate"):
    """Yield per-agent updates for the Streamlit Recherche progress UI.

    Yields dicts:
      {"event": "start", "session_id": str, "agents": [...]}
      {"event": "agent", "agent": str, "output": dict, "state": dict}
      {"event": "done", "state": dict}
      {"event": "error", "error": str, "state": dict | None}
    """
    session_id = str(uuid.uuid4())
    try:
        create_session(session_id, query, user_level)
    except Exception as e:
        logger.warning(f"Failed to create session in database: {e}")

    initial_state = _build_initial_state(query, user_level, session_id)
    graph = build_graph()
    config = {"configurable": {"thread_id": session_id}}

    yield {
        "event": "start",
        "session_id": session_id,
        "agents": [a for a, _ in PIPELINE_AGENTS],
    }

    accumulated: dict = dict(initial_state)
    try:
        for update in graph.stream(initial_state, config, stream_mode="updates"):
            # update = {node_name: partial_state_dict}
            for agent_name, output in update.items():
                partial = output if isinstance(output, dict) else {}
                # claims use operator.add in GraphState — accumulate batches
                # from parallel Extractor Send() branches instead of overwriting.
                merged = {**accumulated, **partial}
                if "claims" in partial:
                    merged["claims"] = list(accumulated.get("claims") or []) + list(
                        partial.get("claims") or []
                    )
                accumulated = merged
                yield {
                    "event": "agent",
                    "agent": agent_name,
                    "output": partial,
                    "state": accumulated,
                }

        final_state = graph.get_state(config).values
        yield {"event": "done", "state": dict(final_state)}
    except Exception as e:
        logger.exception("Pipeline stream failed")
        yield {"event": "error", "error": str(e), "state": accumulated}



if __name__ == "__main__":
    result = run_pipeline("What is RAG?", user_level="beginner")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Query: {result['query']}")
    print(f"Status: {result['status']}")
    print(f"Sub-queries: {result.get('sub_queries', [])}")
    print(f"Sources: {len(result.get('sources', []))}")
    print(f"Claims: {len(result.get('claims', []))}")
