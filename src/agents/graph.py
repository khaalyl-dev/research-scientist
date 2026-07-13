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
from src.agents.state import GraphState
from src.db.crud import create_session
from src.schemas.common import SessionStatus, UserLevel
from src.schemas.source import SourceSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# STUB AGENTS (Planner is real — see planner.py)
# ============================================================================


def researcher_agent(state: GraphState) -> dict:
    """Stub Researcher - searches for sources."""
    print(f"[Researcher] Searching for: {state['sub_queries']}")

    sources = [
        SourceSchema(
            id=str(uuid.uuid4()),
            url=f"https://example.com/source_{i}",
            title=f"Source {i} about {state['query']}",
            source_type="arxiv",
            published_year=2024,
            content=f"Dummy content for source {i}.",
        ).model_dump()
        for i in range(3)
    ]

    return {
        "sources": sources,
        "current_agent": "researcher",
    }


def create_extraction_jobs(state: GraphState) -> List[Send]:
    """Creates one Send() job per source for parallel extraction."""
    return [
        Send("extractor", {"source": source, "session_id": state.get("session_id")})
        for source in state["sources"]
    ]


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
    """Build the LangGraph pipeline."""
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_agent)
    builder.add_node("extractor", extractor_node)
    builder.add_node("fact_checker", fact_checker_agent)
    builder.add_node("reasoner", reasoning_agent)
    builder.add_node("teacher", teacher_agent)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")

    builder.add_conditional_edges("researcher", create_extraction_jobs, ["extractor"])

    builder.add_edge("extractor", "fact_checker")
    builder.add_edge("fact_checker", "reasoner")
    builder.add_edge("reasoner", "teacher")
    builder.add_edge("teacher", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


def run_pipeline(query: str, user_level: str = "intermediate") -> dict:
    """Run the full agent pipeline."""
    # Create session in database
    session_id = str(uuid.uuid4())
    try:
        create_session(session_id, query, user_level)
    except Exception as e:
        logger.warning(f"Failed to create session in database: {e}")

    initial_state: GraphState = {
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

    graph = build_graph()
    config = {"configurable": {"thread_id": session_id}}
    return graph.invoke(initial_state, config)


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
