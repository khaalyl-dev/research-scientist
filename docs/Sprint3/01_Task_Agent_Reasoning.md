# Sprint 3 — Task 1: Agent Reasoning

## Overview

### Objective

Implement the **Reasoning Agent** responsible for synthesizing extracted claims and detected contradictions into a structured, logical answer plan that will be consumed by the **Teacher Agent** to generate the final personalized response.

| Field | Value |
|---|---|
| **Owner** | Zeineb |
| **User Story** | US-06 |
| **Status** | Completed |

---

## Description

The **Reasoning Agent** is the fifth node in the LangGraph pipeline.

It runs after the **Extractor Agent** (and after the **FactChecker Agent** when available) and before the **Teacher Agent**.

Its main responsibility is to transform raw extracted information into a coherent reasoning structure that guides the final response generation.

The agent converts:

- Extracted claims
- Source information
- Confidence values
- Detected contradictions

into a structured markdown answer plan.

---

# Key Responsibilities

## 1. Claim Synthesis

The Reasoning Agent reads all extracted claims from the graph state and organizes them into a meaningful logical structure.

Responsibilities:

- Analyze extracted claims
- Group related concepts
- Identify important information
- Prepare a coherent explanation flow

---

## 2. Contradiction Handling

The agent consumes contradictions produced by the FactChecker Agent when available.

It highlights:

- Conflicting claims
- Differences between sources
- Possible explanations

The system is designed to work even if contradictions are unavailable.

---

## 3. Structured Output Generation

The Reasoning Agent generates a markdown-formatted answer plan containing six sections:

1. Introduction
2. Key Concepts
3. How It Works
4. Evidence Summary
5. Contradictions
6. Conclusion

This structure is then provided to the Teacher Agent.

---

## 4. Graceful Degradation

If the LLM call fails, the agent automatically generates a fallback reasoning plan using available claims.

The fallback mechanism ensures:

- No pipeline interruption
- Useful output generation
- Robustness against LLM failures

---

# Why This Matters

Without the Reasoning Agent, the Teacher Agent would receive unorganized raw claims and contradictions.

The Reasoning Agent provides:

- Logical organization
- Information prioritization
- Better explanation flow
- Improved final answer quality

It acts as the bridge between:

```
Raw Information
        ↓
Reasoning Structure
        ↓
Personalized Final Answer
```

---

# Pipeline Position

```
Planner → Researcher → Extractor → FactChecker → Reasoning → Teacher
```

---

# Implementation

## File Structure

| File | Description |
|---|---|
| `src/agents/reasoning.py` | Complete Reasoning Agent implementation |
| `tests/unit/test_reasoning.py` | Unit tests for the Reasoning Agent |

---

# Core Logic — `reasoning_agent()`

The agent follows these steps:

---

## 1. Read State

The agent extracts required information from the LangGraph state:

```python
query
user_level
claims
contradictions
```

Example:

```python
query = state["query"]
user_level = state["user_level"]
claims = state.get("claims", [])
contradictions = state.get("contradictions", [])
```

---

## 2. Format Data

Claims and contradictions are transformed into readable formats before being injected into the LLM prompt.

Example:

```python
Claim 1:
Entity: RAG
Content: RAG improves factuality
Confidence: 0.9
Source: s1
```

---

## 3. Build Prompt

The agent creates a structured prompt requesting the LLM to generate an answer plan.

The prompt contains:

- User query
- User level
- Extracted claims
- Contradictions

---

## 4. Call LLM

The Reasoning Agent uses:

```
LLMClient
    |
    ├── Groq (Primary)
    |
    └── Ollama (Fallback)
```

---

## 5. Extract Plan

The LLM response is cleaned and stored as a markdown reasoning plan.

---

## 6. Fallback

If the LLM fails:

- Extract the first relevant claims
- Create a simple structured plan
- Include contradiction information if available

---

# Prompt Design

The LLM prompt instructs the model to create a structured reasoning plan.

Required sections:

---

## Introduction

Purpose:

- Introduce the topic
- Explain why it matters

---

## Key Concepts

Purpose:

- Define important concepts
- Explain terminology

---

## How It Works

Purpose:

- Describe mechanisms
- Explain processes

---

## Evidence Summary

Purpose:

- Summarize important claims
- Include source support

---

## Contradictions

Purpose:

- Present disagreements between sources
- Explain conflicting information

---

## Conclusion

Purpose:

- Provide final summary
- Highlight the main takeaway

---

# Output Schema

The Reasoning Agent returns:

```python
{
    "reasoning": str,
    "current_agent": "reasoning"
}
```

Example:

```python
{
    "reasoning": """
    ## Introduction
    
    Retrieval-Augmented Generation combines retrieval systems with language models.
    
    ## Key Concepts
    
    RAG uses external knowledge sources...
    """,

    "current_agent": "reasoning"
}
```

---

# Contradiction Placeholder

The Reasoning Agent supports contradictions before the FactChecker Agent is implemented.

Implementation:

```python
contradictions = state.get("contradictions", [])
```

Benefits:

- Safe execution without FactChecker
- Future compatibility
- Flexible pipeline integration

---

# Fallback Plan

When the LLM fails, the agent creates a basic reasoning structure.

The fallback includes:

- Main concepts from the first 5 claims
- Number of supporting evidence items
- Existing contradictions

Example:

```markdown
## Introduction

Based on available information about the topic.

## Key Concepts

- Concept extracted from claim 1
- Concept extracted from claim 2

## Evidence Summary

5 claims were extracted from available sources.

## Contradictions

No contradictions detected.

## Conclusion

The available evidence supports the explanation.
```

---

# Integration With Existing Components

## Dependencies

| Component | Role |
|---|---|
| `LLMClient` | Groq primary model + Ollama fallback |
| `GraphState` | Reads and updates pipeline state |
| `FactChecker` | Provides contradiction information |

---

# Graph Placement

The Reasoning Agent is inserted between Extractor and Teacher.

```python
builder.add_node(
    "reasoning",
    reasoning_agent
)

builder.add_edge(
    "extractor",
    "reasoning"
)

builder.add_edge(
    "reasoning",
    "teacher"
)
```

---

# FactChecker Interface Contract

The FactChecker Agent must write contradictions into the state using:

```python
state["contradictions"] = [
    {
        "claim_a": "Claim from source A",
        "claim_b": "Claim from source B",
        "similarity_score": 0.87,
        "source_a_id": "source-id-1",
        "source_b_id": "source-id-2",
        "explanation": "Optional explanation"
    }
]
```

---

# Contradiction Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `claim_a` | string | Yes | First conflicting claim |
| `claim_b` | string | Yes | Second conflicting claim |
| `similarity_score` | float | Yes | Similarity score between claims |
| `source_a_id` | string | Yes | Source identifier A |
| `source_b_id` | string | Yes | Source identifier B |
| `explanation` | string | No | Explanation of contradiction |

---

# Testing

## Unit Tests

File:

```
tests/unit/test_reasoning.py
```

The tests use an injected fake LLM client to avoid real API calls.

---

## Test Cases

| Test | Purpose |
|---|---|
| `test_returns_reasoning_with_claims` | Valid reasoning generation with claims |
| `test_handles_empty_claims` | Handles missing claims |
| `test_handles_contradictions` | Includes contradictions correctly |
| `test_llm_failure_falls_back` | Tests fallback mechanism |
| `test_format_claims_empty` | Tests empty claim formatting |
| `test_format_claims_with_claims` | Tests claim formatting |
| `test_format_contradictions_empty` | Tests empty contradiction formatting |
| `test_format_contradictions_with_contradictions` | Tests contradiction formatting |

---

# Manual Testing

Command:

```bash
python -c "
from src.agents.reasoning import reasoning_agent

state = {
    'query': 'What is RAG?',
    'user_level': 'beginner',
    'claims': [
        {
            'entity': 'RAG',
            'claim': 'RAG improves factuality',
            'confidence': 0.9,
            'source_id': 's1'
        },
        {
            'entity': 'RAG',
            'claim': 'RAG uses retrieval',
            'confidence': 0.85,
            'source_id': 's2'
        }
    ],
    'contradictions': [],
}

result = reasoning_agent(state)

print(result['reasoning'])
"
```

---

# Expected Output

A structured markdown reasoning plan containing:

```markdown
## Introduction

## Key Concepts

## How It Works

## Evidence Summary

## Contradictions

## Conclusion
```

---

# Files Modified and Created

| File | Action | Description |
|---|---|---|
| `src/agents/reasoning.py` | Created | Full Reasoning Agent implementation |
| `tests/unit/test_reasoning.py` | Created | Unit test suite |

---

# Handoff Notes for Khalil

## What Is Ready

 Complete Reasoning Agent implementation

 Structured answer plan generation

 Contradiction placeholder support

 LLM failure fallback mechanism

 Unit tests implemented

---

# FactChecker Integration

When implementing the FactChecker Agent:

Add contradictions to the graph state:

```python
state["contradictions"] = [
    {
        "claim_a": "...",
        "claim_b": "...",
        "similarity_score": 0.87,
        "source_a_id": "...",
        "source_b_id": "...",
        "explanation": "..."
    }
]
```

The Reasoning Agent will automatically consume them.

---

# Important Notes

- The agent safely accesses contradictions using:

```python
state.get("contradictions", [])
```

- The system works without FactChecker.
- Contradictions are optional.
- The explanation field improves the final answer quality but is not mandatory.

---

# Task Completion

## Delivered

 Full Reasoning Agent implementation

 Structured reasoning plan generation

 Contradiction placeholder integration

 Fallback reasoning generation

 8 unit tests

---

# Verification

Run:

```bash
pytest tests/unit/test_reasoning.py -v
```

Expected:

```
8 tests passed
```

Additional verification:

```bash
python -c "
from src.agents.reasoning import reasoning_agent
print(' Reasoning Agent OK')
"
```

---

# Status

## Completed 
