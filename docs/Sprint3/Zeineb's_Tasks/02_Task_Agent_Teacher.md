# Sprint 3 — Task 2: Agent Teacher

## Overview

### Objective

Implement the **Teacher Agent** responsible for generating personalized final responses adapted to the user's level (**Beginner, Intermediate, Expert**) with inline citations and a complete source list.

| Field | Value |
|-------|-------|
| **Owner** | Zeineb |
| **User Story** | US-06 |
| **Status** | Completed |

---

## Description

The **Teacher Agent** is the final node in the LangGraph pipeline. It runs after the **Reasoning Agent** and transforms the structured answer plan into a polished, level-adapted final response with inline citations and a complete source list.

---

## Key Responsibilities

### Level Adaptation

Generate responses tailored to the following user levels:

- Beginner
- Intermediate
- Expert

### Inline Citations

Every factual claim must be followed by a citation using the format:

```text
[s1], [s2]
```

### Source List Generation

Automatically compile a complete list of all referenced sources, including their URLs.

### Structured Output

Generate readable markdown using:

- Headings
- Paragraphs
- Bullet points

### Graceful Degradation

If the LLM fails, generate a fallback response from the available claims.

---

## Why This Matters

The **Teacher Agent** is the final output generator. It determines the quality, clarity, and usefulness of the answer the user receives. Without this agent, the pipeline would produce raw reasoning plans instead of polished, readable responses.

---

## Pipeline Position

```text
Planner → Researcher → Extractor → FactChecker → Reasoning → Teacher
```

---

# Implementation

## File Structure

| File | Description |
|------|-------------|
| `src/agents/teacher.py` | Full Teacher Agent implementation |

---

## Core Logic — `teacher_agent()`

The agent follows these steps:

### 1. Read State

Extract the following information from the graph state:

- query
- user_level
- reasoning
- claims
- sources

---

### 2. Format Claims

Transform claims into a readable format including:

- Source IDs
- Confidence scores

---

### 3. Build Prompt

Construct a prompt containing:

- Level-specific writing guidelines
- Citation requirements

---

### 4. Call LLM

Use the **LLMClient** with:

- Groq as the primary model
- Ollama as the fallback model

---

### 5. Clean Response

Remove:

- Markdown fences
- Extra whitespace

---

### 6. Ensure Citations

Verify that inline citations are present.

If citations are missing, append a note indicating that citations should be added.

---

### 7. Add Source List

Append a complete source list if one is not already present in the generated response.

---

## Level Guidelines

| Level | Style |
|-------|-------|
| **Beginner** | Simple language, avoid jargon, use analogies, short sentences, focus on the big picture |
| **Intermediate** | Balance technical accuracy with accessibility, explain technical terms briefly |
| **Expert** | Technical terminology freely, specific paper references, discuss nuances and debates |

---

## Output Schema

```python
{
    "final_response": str,
    "current_agent": "teacher",
    "status": "completed",
}
```

---

## Citation Format

### Inline Citation

```text
RAG improves factual accuracy in LLMs [s1].
```

### Source List

```text
- [s1] Source Title: URL
```

---

## Fallback Response

If the LLM call fails, the agent generates a simple response from the available claims.

The fallback includes:

- Level-appropriate introduction
- Key points with citations
- Summary from the reasoning plan
- Source list

---

# Integration with Existing Components

## Dependencies

| Component | Role |
|-----------|------|
| `LLMClient` | Groq primary + Ollama fallback |
| `GraphState` | Reads query, user_level, reasoning, claims, sources |
| `Reasoning Agent` | Provides the structured answer plan |

---

## Graph Placement

```python
builder.add_node("teacher", teacher_agent)
builder.add_edge("reasoning", "teacher")
builder.add_edge("teacher", END)
```

---

# Testing

## Manual Tests

Four test scenarios were executed to verify the Teacher Agent.

| Test | Scenario | Result |
|------|----------|--------|
| Test 1 | Beginner level with 1 claim | Passed — Simple language, clear citations |
| Test 2 | Intermediate level with 4 claims | Passed — Balanced depth, all claims cited |
| Test 3 | Expert level with 1 claim | Passed — Technical terminology, references |
| Test 4 | Fallback (no API) | Passed — Graceful degradation, key points + sources |

---

## Sample Test Command

```bash
python -c "
from src.agents.teacher import teacher_agent

state = {
    'query': 'What is RAG?',
    'user_level': 'beginner',
    'reasoning': '# Answer Plan\n\nRAG combines retrieval and generation.',
    'claims': [
        {
            'entity': 'RAG',
            'claim': 'RAG improves factuality',
            'confidence': 0.9,
            'source_id': 's1',
            'source_url': 'https://example.com/1'
        },
    ],
    'sources': [
        {
            'id': 's1',
            'title': 'RAG Paper',
            'url': 'https://example.com/1'
        },
    ],
}

result = teacher_agent(state)

print(result['final_response'])
"
```

---

# Files Modified and Created

| File | Action | Description |
|------|--------|-------------|
| `src/agents/teacher.py` | Created | Full Teacher Agent implementation |

---

# Handoff Notes for Khalil

## What is Ready

- `src/agents/teacher.py` fully implemented and tested
- Level adaptation for Beginner, Intermediate, and Expert
- Inline citations using the `[s1]` format with a complete source list
- Fallback response generation when the LLM is unavailable

---

## Important Notes

- The Teacher Agent reads `state["reasoning"]` from the Reasoning Agent.
- It reads `state["claims"]` and `state["sources"]` from the Extractor and Researcher.
- Citations use the format `[s1]`, `[s2]`, where `s1` corresponds to `source_id`.
- The source list is automatically appended if it is not already present in the LLM response.

---

# Task Completion

## Delivered

- Full Teacher Agent implementation
- Level adaptation for Beginner, Intermediate, and Expert
- Inline citation enforcement
- Automatic source list generation
- Fallback response on LLM failure
- Four manual test scenarios, all passing

---

# Verification

```bash
python -c "from src.agents.teacher import teacher_agent; print('Teacher Agent OK')"
```

---

# Status

Completed
