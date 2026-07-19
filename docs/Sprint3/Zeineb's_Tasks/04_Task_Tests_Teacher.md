# Sprint 3 — Task 4: Teacher Tests

## Overview

### Objective

Write comprehensive unit tests for the **Teacher Agent** to verify level adaptation, citation formatting, source list generation, and graceful fallback behavior.

| Field | Value |
|-------|-------|
| **User Story** | US-06 |
| **Status** | Completed |

---

## Description

The **Teacher Tests** provide automated verification of the Teacher Agent's core functionality. The test suite covers all critical aspects of the agent's behavior, from level-specific response generation to error handling and fallback mechanisms.

---

## Why This Matters

Manual testing confirmed the Teacher Agent works, but automated tests are essential for:

- Regression prevention — Catching bugs when code changes
- CI/CD confidence — Ensuring the agent works before deployment
- Refactoring safety — Making changes with confidence
- Documentation — Demonstrating expected behavior through tests

---

# Key Test Areas

- Level adaptation — Beginner, Intermediate, and Expert outputs
- Citation formatting — Correct `[s1]` format
- Source list generation — Complete source list with URLs
- Fallback behavior — Graceful degradation without API
- Edge cases — Empty claims and missing sources
- Formatting helpers — Claims and source formatting

---

# Implementation

## File Structure

| File | Description |
|------|-------------|
| `tests/unit/test_teacher.py` | Unit tests for the Teacher Agent |

---

## Test Classes

| Class | Purpose |
|-------|---------|
| `TestTeacherAgent` | Tests for the main `teacher_agent()` function |
| `TestFormatHelpers` | Tests for formatting helper functions |

---

## Test Coverage

| Test | Purpose |
|------|---------|
| `test_teacher_generates_beginner_response` | Beginner-level response generation |
| `test_teacher_generates_intermediate_response` | Intermediate-level response generation |
| `test_teacher_generates_expert_response` | Expert-level response generation |
| `test_handles_empty_claims` | Empty claims edge case |
| `test_llm_failure_falls_back` | Fallback on LLM failure |
| `test_ensures_citations_are_present` | Citation enforcement |
| `test_skips_citations_if_present` | Prevents duplicate citations |
| `test_format_claims_with_sources` | Claim formatting |
| `test_format_claims_empty` | Empty claim formatting |
| `test_format_sources` | Source formatting |
| `test_format_sources_empty` | Empty source formatting |
| `test_clean_response_removes_fences` | Markdown fence removal |
| `test_clean_response_strips_whitespace` | Whitespace cleanup |
| `test_build_fallback_response` | Fallback response generation |

---

# Dependencies

## Fake LLM Client

A fake LLM client is used in all tests to avoid real API calls.

```python
class FakeLLMClient:
    def __init__(self, response: str = "", raise_exc: Exception | None = None):
        self.response = response
        self.raise_exc = raise_exc
        self.calls = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self.raise_exc:
            raise self.raise_exc
        return self.response
```

---

## Test State Factory

A helper function creates a consistent test state.

```python
def make_state(
    query: str = "What is RAG?",
    user_level: str = "intermediate",
    reasoning: str = "# Answer Plan\n\nRAG combines retrieval and generation.",
    claims=None,
    sources=None,
):
    return {
        "query": query,
        "user_level": user_level,
        "reasoning": reasoning,
        "claims": claims or [],
        "sources": sources or [],
    }
```

---

# Running the Tests

## Command

```bash
pytest tests/unit/test_teacher.py -v
```

---

## Expected Output

```text
collected 14 items

test_teacher.py::TestTeacherAgent::test_teacher_generates_beginner_response PASSED
test_teacher.py::TestTeacherAgent::test_teacher_generates_intermediate_response PASSED
test_teacher.py::TestTeacherAgent::test_teacher_generates_expert_response PASSED
test_teacher.py::TestTeacherAgent::test_handles_empty_claims PASSED
test_teacher.py::TestTeacherAgent::test_llm_failure_falls_back PASSED
test_teacher.py::TestTeacherAgent::test_ensures_citations_are_present PASSED
test_teacher.py::TestTeacherAgent::test_skips_citations_if_present PASSED
test_teacher.py::TestFormatHelpers::test_format_claims_with_sources PASSED
test_teacher.py::TestFormatHelpers::test_format_claims_empty PASSED
test_teacher.py::TestFormatHelpers::test_format_sources PASSED
test_teacher.py::TestFormatHelpers::test_format_sources_empty PASSED
test_teacher.py::TestFormatHelpers::test_clean_response_removes_fences PASSED
test_teacher.py::TestFormatHelpers::test_clean_response_strips_whitespace PASSED
test_teacher.py::TestFormatHelpers::test_build_fallback_response PASSED

===================== 14 passed in 0.5s ======================
```

---

# Files Modified and Created

| File | Action | Description |
|------|--------|-------------|
| `tests/unit/test_teacher.py` | Created | 14 unit tests for the Teacher Agent |

---

# Handoff Notes for Khalil

## What is Ready

- `tests/unit/test_teacher.py` complete test suite for the Teacher Agent
- All tests use a fake LLM client; no API keys are required
- Tests verify level adaptation, citation handling, and fallback behavior

---

## Important Notes

- Tests run in CI without requiring API keys.
- The fake LLM client simulates both successful and failed LLM responses.
- Additional user levels can be tested by extending the existing test suite.

---

# Task Completion

## Delivered

- 14 unit tests for the Teacher Agent
- Level adaptation tests for Beginner, Intermediate, and Expert
- Citation validation tests
- Fallback response tests
- Formatting helper tests

---

# Verification

```bash
pytest tests/unit/test_teacher.py -v
```

Expected result:

```text
14 tests passed
```

---

# Status

Completed
