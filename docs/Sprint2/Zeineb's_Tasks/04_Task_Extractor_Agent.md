# Sprint 2 — Task 4: Extractor Agent

## Overview

### Objective
Implement the Extractor Agent, which runs once per source via LangGraph's `Send()` fan-out, calling the LLM to pull structured, validated claims out of each source's text.

| Field | Value |
|--------|-------|
| **Owner** | Zeineb |
| **Status** | Completed |

---

## Description

The Extractor Agent is the third node in the LangGraph pipeline, and the first agent to actually call an LLM. It runs in parallel — one instance per source found by the Researcher — via LangGraph's `Send()` API, and every instance's output merges automatically into `state["claims"]` through the `operator.add` reducer.

### Key Responsibilities

- **LLM-based extraction** — build a prompt from a source's title and content, call `LLMClient.generate()` (Task 3), and parse the response into structured claims.
- **Robust JSON parsing** — LLMs routinely wrap JSON in markdown fences or add prose around it despite instructions; the parser handles both instead of failing on the first deviation from a perfectly clean response.
- **Per-claim validation** — every claim is validated through `ClaimSchema` (confidence range, required fields); one malformed claim in an otherwise-good batch is dropped, not fatal to the rest.
- **Graceful degradation** — an LLM failure (Groq and Ollama both down), a malformed response, or empty source content all degrade to zero claims for that source, never a crash.
- **msgpack-safe output** — claims are converted to dicts via `.model_dump()` before returning, per the rule established in Task 1.
- **No shared-key writes** — returns only `{"claims": [...]}`, deliberately never `current_agent` or any other single-value key, avoiding the exact parallel-write conflict documented in Task 1's "Issues Encountered" table.

### Why This Matters

Without the Extractor, `state["claims"]` only ever contains stub data — there is no real content for FactChecker, Reasoning, or Teacher to work with. This is the agent that makes the pipeline's output actually reflect the sources it found.

---

## Implementation

### File Structure

| File | Description |
|------|-------------|
| `src/agents/extractor.py` | Full Extractor Agent implementation |
| `tests/unit/test_extractor.py` | 13 unit tests |

### Core Logic — `extractor_node()`

Unlike every other node in the graph, this one does **not** receive the full `GraphState`. `Send()` constructs a small standalone dict per branch:

```python
{"source": <source dict>, "session_id": <str>}
```

The node:

1. Reads `title`, `content`, `id`, and `url` from `state["source"]` (a dict, per Task 1's msgpack rule).
2. Skips the LLM call entirely if content is empty — no point spending an API call on nothing.
3. Builds a prompt instructing the LLM to return a JSON array of `{entity, claim, confidence}` objects, capped at 6 claims.
4. Calls `LLMClient.generate(prompt)`.
5. Parses the response, validates each claim through `ClaimSchema`, converts to dicts.
6. Returns `{"claims": [...]}` — nothing else.

### Robust JSON Extraction

Real LLM responses are messy in predictable ways. `_extract_json_array()` handles:

- Markdown-fenced JSON (` ```json ... ``` `)
- Prose wrapped around the JSON ("Sure, here are the claims:\n[...]\nHope that helps!")
- A clean, empty array (`[]`) when the source has no clear factual claims

### Prompt Design

Source content is truncated to 6,000 characters before being included in the prompt — keeps latency and Groq token cost bounded for very long scraped pages without needing a separate chunking system yet.

### Integration with Existing Clients

**`LLMClient`** (Task 3, `src/clients/llm_client.py`)

```python
LLMClient().generate(prompt: str) -> str
```

- Tries Groq first, falls back to Ollama automatically, raises `RuntimeError` if both fail.
- `extractor_node`'s `try/except` around `generate()` catches that `RuntimeError` (and any other exception) and returns an empty claims list instead of propagating — one source's LLM failure cannot crash the other parallel `Send()` branches.

---

## Testing

### Unit Tests

`tests/unit/test_extractor.py` — 13 tests, all using an injected fake LLM client (no real API calls):

| Test | Purpose |
|------|---------|
| `test_extracts_valid_claims_from_clean_json` | Happy path |
| `test_returns_claims_as_dicts_not_objects` | msgpack-safety rule enforced |
| `test_handles_markdown_fenced_json` | Real LLM formatting quirk |
| `test_handles_prose_wrapped_around_json` | Real LLM formatting quirk |
| `test_empty_array_response_yields_no_claims` | Clean "nothing found" case |
| `test_completely_malformed_response_degrades_to_empty_not_exception` | No crash on garbage output |
| `test_one_malformed_claim_does_not_discard_valid_siblings` | Partial-batch resilience |
| `test_confidence_out_of_range_is_dropped_not_fatal` | Schema validation enforced |
| `test_llm_exception_does_not_crash_returns_empty_claims` | US-13 compliance |
| `test_empty_source_content_skips_llm_call_entirely` | No wasted API calls |
| `test_does_not_return_current_agent_key` | Regression guard for Task 1's documented parallel-write bug |
| `test_caps_claims_at_max_per_source` | `MAX_CLAIMS_PER_SOURCE` enforced |
| `test_content_truncated_in_prompt_for_very_long_sources` | Prompt size bounded |

```bash
pytest tests/unit/test_extractor.py -v
# 13 passed
```

### Real End-to-End Verification (Beyond Unit Tests)

Unit tests call `extractor_node()` directly and don't exercise LangGraph's actual checkpointer. Since Task 1 found a real msgpack serialization bug that only appeared under real checkpointing, this agent was additionally verified by wiring it into the **real, unmodified `graph.py`** and running the full pipeline through the real `MemorySaver` checkpointer, with only the network boundary (`ChatGroq.invoke`) mocked:

**Scenario 1 — no LLM reachable (no API key, no local Ollama):**

```
Sources: 3
Claims: 0
Status: completed
```
All 3 parallel `Send()` branches degraded gracefully; pipeline still completed end-to-end with no crash.

**Scenario 2 — mocked successful Groq responses:**

```
Sources: 3
Claims merged via operator.add: 3
 - claim from source 0
 - claim from source 1
 - claim from source 2
Status: completed
```
Confirms real claims from 3 concurrent parallel branches correctly merge into one list via the `operator.add` reducer, survive real msgpack checkpointing, and flow through to FactChecker/Reasoning/Teacher correctly.

---

## Issues Encountered & Resolutions

| Issue | Resolution |
|-------|------------|
| LLM response wrapped in markdown fences or surrounding prose | Regex-based extraction of the first `[...]` block instead of assuming clean JSON |
| One malformed claim could discard an entire valid batch | Per-claim `try/except`; only the bad claim is dropped |
| Risk of repeating Task 1's parallel-write bug (`current_agent` conflict) | Node deliberately returns only `{"claims": [...]}`; regression test locks this in |
| Unit tests alone wouldn't catch a real checkpointing failure (per Task 1's precedent) | Added a second verification pass through the real graph + real `MemorySaver`, not just isolated unit tests |

---

## Files Modified / Created

| File | Action | Description |
|------|--------|-------------|
| `src/agents/extractor.py` | Created | Full Extractor Agent implementation |
| `tests/unit/test_extractor.py` | Created | 13 unit tests |
| `src/agents/graph.py` | Modified | Replaced stub `extractor_agent` with real `extractor_node` in `add_node()` and the import |

---

## Handoff Notes for Khalil

### What's Ready

**`src/agents/extractor.py`**
- Fully implemented and verified, both in isolation and through the real graph.

**`src/agents/graph.py`**
- The `extractor` node now runs real logic. The stub `extractor_agent` function is still present but unused — safe to delete.

### Important Notes

- The Extractor expects `state["source"]` to be a **dict**, not a `SourceSchema` object — this is guaranteed by the Researcher Agent's own `.model_dump()` conversion (Task 2) and Send()'s pass-through.
- Do not add `current_agent` (or any other non-reducer key) to this node's return — see the regression test and Task 1's documented bug.
- `researcher_node` (Task 2) is **not yet wired into `graph.py`** — it's `async`, and this graph currently runs via sync `graph.invoke()`. That compatibility needs a dedicated check before swapping in, separate from this task.

---

## Task Completion

### Delivered
- Extractor Agent with real Groq/Ollama-backed claim extraction
- Robust parsing of messy real-world LLM output (markdown fences, prose wrapping)
- Per-claim validation with partial-batch resilience
- Graceful degradation on LLM failure (US-13)
- msgpack-safe dict output
- Parallel-write conflict avoided (regression-tested)
- 13 unit tests, all passing
- Verified end-to-end through the real graph and real checkpointer, both failure and success paths

### Verification

```bash
pytest tests/unit/test_extractor.py -v
# 13 passed

pytest tests/unit/ -v
# 39 passed (full suite)

python -m src.agents.graph
# Sources: 3, Claims: 3 (with mocked successful LLM), Status: completed
```

## Final Status

**Task Completed**
