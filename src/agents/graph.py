"""
LangGraph graph builder for the agent pipeline.
"""

import uuid
from typing import List

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from src.agents.state import GraphState
from src.schemas.claim import ClaimSchema
from src.schemas.common import SessionStatus, UserLevel
from src.schemas.source import SourceSchema

# ============================================================================
# STUB AGENTS
# ============================================================================


def planner_agent(state: GraphState) -> dict:
    """Stub Planner - decomposes query into sub-queries."""
    print(f"[Planner] Processing: {state['query']}")

    sub_queries = [
        f"{state['query']} - overview",
        f"{state['query']} - key concepts",
        f"{state['query']} - applications",
    ]

    return {
        "sub_queries": sub_queries,
        "current_agent": "planner",
        "status": SessionStatus.running.value,
    }


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


def extractor_agent(state: dict) -> dict:
    """Stub Extractor - extracts claims from a source."""
    source = state.get("source")
    print(f"[Extractor] Processing: {source['title'] if source else 'unknown'}")

    claims = [
        ClaimSchema(
            id=str(uuid.uuid4()),
            source_id=source["id"] if source else str(uuid.uuid4()),
            source_url=source["url"] if source else "",
            entity=f"Concept_{i}",
            claim=f"Claim {i} about {source['title'] if source else 'unknown'}",
            confidence=0.85 + (i * 0.05),
        ).model_dump()
        for i in range(2)
    ]

    return {"claims": claims}


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

    builder.add_node("planner", planner_agent)
    builder.add_node("researcher", researcher_agent)
    builder.add_node("extractor", extractor_agent)
    builder.add_node("fact_checker", fact_checker_agent)
    builder.add_node("reasoning", reasoning_agent)
    builder.add_node("teacher", teacher_agent)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")

    builder.add_conditional_edges("researcher", create_extraction_jobs, ["extractor"])

    builder.add_edge("extractor", "fact_checker")
    builder.add_edge("fact_checker", "reasoning")
    builder.add_edge("reasoning", "teacher")
    builder.add_edge("teacher", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


def run_pipeline(query: str, user_level: str = "intermediate") -> dict:
    """Run the full agent pipeline."""
    initial_state: GraphState = {
        "query": query,
        "user_level": UserLevel(user_level),
        "session_id": str(uuid.uuid4()),
        "status": SessionStatus.running.value,
        "current_agent": "start",
        "retry_count": 0,
        "sub_queries": [],
        "sources": [],
        "claims": [],
        "contradictions": [],
        "has_contradictions": False,
        "reasoning": "",
        "final_response": "",
        "error": None,
    }

    graph = build_graph()
    config = {"configurable": {"thread_id": initial_state["session_id"]}}
    return graph.invoke(initial_state, config)


if __name__ == "__main__":
    result = run_pipeline("What is RAG?", user_level="beginner")

    print("\n" + "=" * 60)
    print("🚀 PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Query: {result['query']}")
    print(f"Status: {result['status']}")
    print(f"Sources: {len(result.get('sources', []))}")
    print(f"Claims: {len(result.get('claims', []))}")
