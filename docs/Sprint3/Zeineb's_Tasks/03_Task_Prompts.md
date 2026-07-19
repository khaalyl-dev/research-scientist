# Sprint 3 — Task 3: Prompts (Beginner vs Expert)

## Overview

### Objective

Design and implement level-specific prompts for the **Teacher Agent** that adapt the response style, vocabulary, and depth for **Beginner**, **Intermediate**, and **Expert** users, ensuring each level produces a distinctly different output.

| Field | Value |
|-------|-------|
| **Owner** | Zeineb |
| **User Story** | US-06 |
| **Status** | Completed |

---

## Description

The **Prompts** task defines three distinct prompt templates that control how the **Teacher Agent** generates responses. Each prompt is tailored to a specific user level, ensuring that the final answer matches the user's expertise and needs.

---

## Why This Matters

Without level-specific prompts, all users would receive the same response regardless of their expertise. A beginner would be overwhelmed by technical jargon, while an expert would be frustrated by oversimplification.

These prompts ensure that every user receives an answer that is appropriate for their level.

---

# The Three Levels

| Level | Audience | Style |
|-------|----------|-------|
| **Beginner** | New to the topic, no prior knowledge | Simple language, analogies, big picture focus |
| **Intermediate** | Some background knowledge | Balanced technical depth, clear explanations |
| **Expert** | Deep domain expertise | Technical terminology, paper references, nuanced analysis |

---

# Implementation

## File Structure

| File | Description |
|------|-------------|
| `prompts/teacher_prompts.py` | Level-specific prompt templates and router |
| `tests/unit/test_teacher_prompts.py` | Unit tests for the prompt system |
| `prompts/__init__.py` | Package exports |

---

# Level-Specific Prompts

## Beginner Prompt

Characteristics:

- Uses simple, everyday language
- Avoids jargon or explains it clearly
- Uses concrete examples and analogies
- Short paragraphs with clear headings
- Warm, encouraging, conversational tone
- Focuses on the big picture and core concepts

### Example Excerpt

> "Imagine you have a research assistant who can read every book in the library in seconds and then summarize the most important parts for you..."

---

## Intermediate Prompt

Characteristics:

- Balances technical accuracy with accessibility
- Uses technical terms with brief explanations
- Assumes familiarity with basic concepts
- Professional, clear, and confident tone
- Explains mechanisms and processes
- Includes relevant nuances

### Example Excerpt

> "Retrieval-Augmented Generation (RAG) addresses a fundamental limitation of LLMs: they rely solely on their training data for knowledge..."

---

## Expert Prompt

Characteristics:

- Uses technical terminology freely
- Assumes deep expertise
- Discusses specific methodologies, papers, and debates
- Precise, analytical, and rigorous tone
- Comprehensive citations throughout
- Discusses open questions and future directions

### Example Excerpt

> "Retrieval-Augmented Generation (Lewis et al., 2020) addresses the parametric knowledge limitations of transformer-based LLMs..."

---

# Prompt Router

The `get_teacher_prompt()` function returns the appropriate prompt template based on the user's level.

```python
def get_teacher_prompt(user_level: str) -> str:
    level_map = {
        "beginner": BEGINNER_PROMPT,
        "intermediate": INTERMEDIATE_PROMPT,
        "expert": EXPERT_PROMPT,
    }
    return level_map.get(user_level.lower(), INTERMEDIATE_PROMPT)
```

---

# Integration with Teacher Agent

The Teacher Agent uses the level-specific prompts during response generation.

```python
from prompts.teacher_prompts import get_teacher_prompt

level_prompt = get_teacher_prompt(user_level)

prompt = level_prompt.format(
    query=query,
    user_level=user_level,
    reasoning=reasoning,
    claims_with_sources=claims_text,
)
```

---

# Testing

## Unit Tests

File:

```
tests/unit/test_teacher_prompts.py
```

The prompt system is validated using the following tests.

| Test | Purpose |
|------|---------|
| `test_get_teacher_prompt_beginner` | Returns beginner prompt for `"beginner"` level |
| `test_get_teacher_prompt_intermediate` | Returns intermediate prompt for `"intermediate"` level |
| `test_get_teacher_prompt_expert` | Returns expert prompt for `"expert"` level |
| `test_get_teacher_prompt_default` | Returns intermediate prompt for unknown level |
| `test_build_prompt_context` | Builds the full prompt context |
| `test_beginner_prompt_has_analogies` | Beginner prompt emphasizes analogies |
| `test_intermediate_prompt_has_balance` | Intermediate prompt emphasizes balanced explanations |
| `test_expert_prompt_has_technical_depth` | Expert prompt emphasizes technical depth |

---

## Manual Verification

Three manual tests were executed to verify that each prompt produces the expected output style.

| Test | Result |
|------|--------|
| Beginner level | Passed — Simple language, analogies, big picture |
| Intermediate level | Passed — Balanced technical depth |
| Expert level | Passed — Technical terminology, paper references |

---

# Files Modified and Created

| File | Action | Description |
|------|--------|-------------|
| `prompts/teacher_prompts.py` | Created | Level-specific prompt templates and router |
| `tests/unit/test_teacher_prompts.py` | Created | Unit tests for the prompt system |
| `prompts/__init__.py` | Created | Package exports |
| `src/agents/teacher.py` | Modified | Integrated level-specific prompts |

---

# Handoff Notes for Khalil

## What is Ready

- `prompts/teacher_prompts.py` fully implemented with three prompt levels
- Prompt router for automatic level detection
- Integration with the Teacher Agent using level-specific prompts

---

## Important Notes

- The prompts are stored as Python string templates in `teacher_prompts.py`.
- Additional user levels can be introduced by extending the `level_map` dictionary.
- The prompt router defaults to the **Intermediate** prompt for unknown levels.
- Manual testing confirms that each prompt produces a distinct output style.

---

# Task Completion

## Delivered

- Beginner prompt template
- Intermediate prompt template
- Expert prompt template
- Prompt router with automatic level detection
- Prompt context builder
- Integration with the Teacher Agent
- Unit tests for the prompt system
- Manual verification for all three user levels

---

# Verification

```bash
pytest tests/unit/test_teacher_prompts.py -v
```

Expected result:

```
7 tests passed
```

---

## Manual Verification

| Level | Query | Output Style |
|------|-------|--------------|
| Beginner | "What is RAG?" | Simple language, analogies |
| Intermediate | "What is RAG?" | Balanced technical depth |
| Expert | "What is RAG?" | Technical terminology, citations |

---

# Status

Completed
