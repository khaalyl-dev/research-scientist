"""
LangGraph graph builder for the agent pipeline.

Wires Sprint 2 agents + Sprint 3 FactChecker / Reasoning / Teacher
(Zeineb's reasoning.py & teacher.py — imported, not modified).
"""

import uuid
from pathlib import Path
from typing import List

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from src.agents.extractor import extractor_node
from src.agents.fact_checker import fact_checker_agent
from src.agents.planner import planner_node
from src.agents.reasoning import reasoning_agent
from src.agents.researcher import researcher_node
from src.agents.state import GraphState
from src.agents.teacher import teacher_agent
from src.db.crud import create_session, save_final_response
from src.knowledge.graph import KnowledgeGraph
from src.schemas.common import SessionStatus, UserLevel
from src.utils.logger import get_logger

logger = get_logger(__name__)

_GRAPH_DIR = Path(__file__).resolve().parents[2] / "data" / "graphs"


async def researcher_agent(state: GraphState) -> dict:
    """Real Researcher — arXiv/web/wiki/scholar/OpenAlex/PubMed; sources as dicts."""
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
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, researcher_agent(state)).result()


def create_extraction_jobs(state: GraphState) -> List[Send] | str:
    """Fan-out: one parallel Extractor `Send()` per source (US-04)."""
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


dispatch_to_extractors = create_extraction_jobs


def _build_and_export_knowledge_graph(state: GraphState) -> str | None:
    """Consume Zeineb's KnowledgeGraph API — build from claims, export JSON."""
    claims = state.get("claims") or []
    session_id = state.get("session_id") or "unknown"
    if not claims:
        return None
    try:
        kg = KnowledgeGraph(session_id=session_id)
        claim_dicts = [
            c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in claims
        ]
        kg.build_from_claims(claim_dicts)
        _GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        path = _GRAPH_DIR / f"{session_id}.json"
        kg.export_json(path)
        return str(path)
    except Exception as e:
        logger.warning(f"Knowledge graph build/export failed: {e}")
        return None


def reasoner_node(state: GraphState) -> dict:
    """Wrapper: Zeineb Reasoning + build NetworkX KG for the Graphe page."""
    result = dict(reasoning_agent(state))
    graph_path = _build_and_export_knowledge_graph(state)
    if graph_path:
        try:
            meta = _GRAPH_DIR / f"{state.get('session_id')}.path"
            meta.write_text(graph_path, encoding="utf-8")
        except Exception:
            pass
    result["current_agent"] = "reasoner"
    return result


def teacher_node(state: GraphState) -> dict:
    """Wrapper: Zeineb Teacher + persist final response / session status."""
    result = dict(teacher_agent(state))
    session_id = state.get("session_id")
    final = result.get("final_response") or ""
    if session_id and final:
        try:
            save_final_response(session_id, final)
        except Exception as e:
            logger.warning(f"Failed to save final response: {e}")
            try:
                from src.db.crud import update_session_status

                update_session_status(session_id, SessionStatus.completed.value)
            except Exception as e2:
                logger.warning(f"Failed to update session status: {e2}")
    result["current_agent"] = "teacher"
    result["status"] = SessionStatus.completed.value
    return result


def build_graph():
    """Build the LangGraph pipeline with parallel Extractor fan-out."""
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", _sync_researcher_agent)
    builder.add_node("extractor", extractor_node)
    builder.add_node("fact_checker", fact_checker_agent)
    builder.add_node("reasoner", reasoner_node)
    builder.add_node("teacher", teacher_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")

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
    """Yield per-agent updates for the Streamlit Recherche progress UI."""
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
            for agent_name, output in update.items():
                partial = output if isinstance(output, dict) else {}
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
    print(f"Contradictions: {len(result.get('contradictions', []))}")
