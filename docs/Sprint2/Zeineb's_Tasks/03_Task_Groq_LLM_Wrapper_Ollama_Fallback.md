# Sprint 2 — Task 3: Groq LLM Wrapper with Ollama Fallback

## Overview

### Objective

Implement a robust LLM client that provides a unified interface for calling Groq's Llama 3.3 70B model with automatic fallback to local Ollama when Groq is unavailable or fails.

| Field | Value |
|---|---|
| Owner | Zeineb |
| Estimate | 2 hours |
| Status | Completed |

## Description

The Groq LLM Wrapper is a foundational component that enables all downstream agents (Planner, Extractor, Reasoning, Teacher) to access large language models without worrying about API availability or failure handling.

Key responsibilities:

- Centralize LLM provider access
- Provide a unified generation interface
- Handle provider failures automatically
- Switch transparently between Groq and Ollama

---

# Key Responsibilities

## Unified Interface

Provide a single `generate()` method that any agent can call.

Example:

```python
response = LLMClient().generate(prompt)
```
Agents do not need to manage LLM provider logic.

Primary LLM

The primary LLM provider is Groq.

Property	Value
Provider	Groq
Model	Llama 3.3 70B
Integration	langchain-groq
Model Name	llama-3.3-70b-versatile

Advantages:

High inference speed
Free tier availability
Large-scale reasoning capabilities
Automatic Fallback

The client automatically switches to local Ollama when Groq fails.

Fallback scenarios:

API failure
Rate limit reached
Network error
Model unavailable
Service interruption

Flow:

Agent Request
      |
      v
LLMClient.generate()
      |
      v
Try Groq Llama 3.3 70B
      |
      +---- Success --> Return response
      |
      +---- Failure
              |
              v
        Try Ollama Model
              |
              +---- Success --> Return response
              |
              +---- Failure --> Raise Error
File Structure
File	Description
src/clients/llm_client.py	LLM client with Groq + Ollama fallback
tests/unit/test_llm_client.py	Unit tests for the client
requirements.txt	Added langchain-ollama dependency
Implementation
LLMClient Class

The LLMClient class is responsible for:

Loading configuration from .env
Initializing LLM providers lazily
Calling Groq as the primary provider
Calling Ollama as fallback
Handling errors and logging warnings
generate() Method

The public method follows three steps:

1. Try Groq First

If:

GROQ_API_KEY exists
The model is available

The request is sent to Groq.

2. Fallback to Ollama

If Groq fails and fallback is enabled:

GROQ_FALLBACK=ollama

The request is automatically redirected to the local Ollama model.

3. Raise Error

If both providers fail:

The error is propagated clearly
No silent failure occurs
Groq Integration

Uses LangChain Groq:

from langchain_groq import ChatGroq

Configuration:

LLM_MODEL=llama-3.3-70b-versatile
Ollama Integration

Uses LangChain Ollama:

from langchain_ollama import ChatOllama

Fallback model:

OLLAMA_MODEL_QUALITY=llama3.1:8b
Configuration
Environment Variables
Variable	Description	Example
GROQ_API_KEY	Groq API key	gsk_...
GROQ_FALLBACK	Enable Ollama fallback	ollama or none
LLM_MODEL	Groq model name	llama-3.3-70b-versatile
OLLAMA_MODEL_QUALITY	Ollama fallback model	llama3.1:8b
.env Example
GROQ_API_KEY=gsk_your_key_here

GROQ_FALLBACK=ollama

LLM_MODEL=llama-3.3-70b-versatile

OLLAMA_MODEL_QUALITY=llama3.1:8b
Testing
Unit Tests

File:

tests/unit/test_llm_client.py

The client is tested by:

Mocking Groq

Tests:

Successful Groq response
Groq failure scenarios
Mocking Ollama

Tests:

Correct fallback execution
Ollama response handling
Environment Overrides

Tests:

Different configurations
Fallback enabled/disabled behavior
Manual Testing

Command:

python -c "
from src.clients.llm_client import LLMClient

client = LLMClient()

response = client.generate('Say hello in one word')

print(response)
"

Expected output:

Hello
Issues Encountered & Resolutions
Issue	Resolution
ModuleNotFoundError: No module named 'langchain_ollama'	Installed langchain-ollama and added it to requirements.txt
Model llama3.1:8b not found	Pulled the model using ollama pull llama3.1:8b
Model llama-3.1-70b-versatile decommissioned	Updated to llama-3.3-70b-versatile
Files Modified / Created
File	Action	Description
src/clients/llm_client.py	Created	Groq LLM client with Ollama fallback
requirements.txt	Modified	Added langchain-ollama==0.1.*
.env	Modified	Added LLM configuration variables
Handoff Notes for Khalil
What's Ready

The LLM client is ready:

src/clients/llm_client.py

Usage:

from src.clients.llm_client import LLMClient

client = LLMClient()

response = client.generate(prompt)
Important Notes
Groq is used by default.
Ollama is used automatically when Groq fails.
Disable fallback with:
GROQ_FALLBACK=none
Configure fallback model using:
OLLAMA_MODEL_QUALITY
Ensure Groq API key is configured:
GROQ_API_KEY=gsk_xxxxxxxxx
Task Completion
Delivered

LLM client with Groq + Ollama fallback
Unified generate() interface
Environment-based configuration
Error handling and logging
Updated requirements.txt
Unit tests

Verification

Run:

python -c "
from src.clients.llm_client import LLMClient

print('LLM Client OK')
"

Expected output:

LLM Client OK
Status

Task Completed
