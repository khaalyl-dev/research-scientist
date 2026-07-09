# Autonomous Research Scientist

Ask a question. Get a structured, cited, personalized answer — synthesized from arXiv and the web by a team of cooperating AI agents, with contradictions flagged, sources traceable, and a knowledge graph you can explore.

**Team:** Khalil & Zeineb · **Timeline:** 8 weeks, 4 sprints

---

## What it does

Given a natural-language question and a target level (Beginner / Intermediate / Expert), the system:

- Decomposes the question into 3-5 focused sub-queries
- Searches arXiv and the web in parallel for relevant sources
- Extracts structured, confidence-scored claims from every source
- Detects contradictions between sources and surfaces the disagreement
- Synthesizes a personalized answer with inline, clickable citations
- Streams the answer progressively instead of a blocking wait
- Visualizes an interactive knowledge graph of the concepts involved
- Generates a shareable Research Notebook with an Evidence Score
- Remembers what it has learned across sessions (Knowledge Memory)
- Exports everything to CSV/JSON

**Explicitly out of scope for the MVP** (candidates for V2): PDF upload, multi-user collaboration, and a non-Streamlit frontend.

---

## How it works

A LangGraph state machine runs six agents in sequence, with extraction parallelized across sources:

Planner -> Researcher (parallel) -> Extractor (parallel per source) -> FactChecker -> Reasoning -> Teacher

| Agent | Job |
|-------|-----|
| Planner | Breaks the question into sub-queries |
| Researcher | Searches arXiv + Brave Search in parallel |
| Extractor | Pulls structured claims out of each source |
| FactChecker | Compares claims via embeddings, flags contradictions |
| Reasoning | Synthesizes a structured plan for the answer |
| Teacher | Writes the final answer, adapted to the user's level |
| Memory | Remembers past research for contextual answers |

Everything persists to SQLite (sessions/sources/claims/contradictions) and FAISS (vector search); the knowledge graph is maintained in NetworkX and rendered with pyvis inside Streamlit.

Full design rationale is in `architecture.md`.

---

## Tech Stack

100% free tier, no credit card required.

| Layer | Choice |
|-------|--------|
| Orchestration | LangGraph |
| LLM | Groq (Llama 3.1 70B), fallback Ollama |
| Web search | Brave Search API, fallback DuckDuckGo |
| Academic search | arXiv API |
| Page scraping | BeautifulSoup + requests |
| Vector search | FAISS + sentence-transformers |
| Storage | SQLite + SQLAlchemy + Alembic |
| Knowledge graph | NetworkX + pyvis |
| Frontend | Streamlit |

Full pinned versions in `requirements.txt`.

---

## Project Status

### Sprint 1 — Foundations and Ingestion (Complete)

The data layer, search clients, and documentation are complete:

| Component | Status |
|-----------|--------|
| Project skeleton and tooling | Done |
| SQLAlchemy models + Alembic migrations | Done |
| Pydantic schemas (in-memory agent state) | Done |
| Brave Search client + DuckDuckGo fallback | Done |
| Unit tests (17 tests, 99% coverage) | Done |
| README + architecture documentation | Done |
| Docker + CI | Done |
| arXiv client | Pending (Khalil) |
| BeautifulSoup scraper | Pending (Khalil) |
| Streamlit base UI | Pending (Khalil + Zeineb) |

### Sprint 2 — Agents and Semantic Search (In Progress)

Building the agent pipeline and semantic search:

| Component | Status |
|-----------|--------|
| LangGraph agent orchestration | In Progress |
| Planner Agent | Pending |
| Researcher Agent | Pending |
| Extractor Agent | Pending |
| FAISS vector search pipeline | Pending |
| Streaming UI with agent progress | Pending |

### Sprint 3 — Contradictions, Graph and Personalization (Upcoming)

- FactChecker Agent (contradictions)
- Reasoning Agent (synthesis)
- Teacher Agent (personalization)
- Knowledge graph with NetworkX + pyvis
- Claims and contradictions UI

### Sprint 4 — Finalization and Demo (Upcoming)

- Memory Agent (cross-session learning)
- History page and exports (CSV/JSON)
- Research Notebook with Evidence Score
- End-to-end testing and optimization
- Demo preparation

---

## Getting Started

**Prerequisites:** Python 3.11+, free API keys for Groq and Brave Search.

```bash
# 1. Clone and enter the repo
git clone https://github.com/khaalyl-dev/research-scientist.git
cd research-scientist

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
Edit .env and fill in:

GROQ_API_KEY=gsk_...        # free at console.groq.com
BRAVE_API_KEY=BSA...        # free at brave.com/search/api
bash
# 5. Initialize the database
alembic upgrade head

# 6. Run the app (once UI is ready)
streamlit run app/main.py
Running Tests

# Full suite
pytest tests/unit/ -v

# With coverage
pytest --cov=src tests/unit/ --cov-report=term-missing
No API keys required — all external calls are mocked.

Database Migrations

# After changing a model:
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
Code Quality
bash
black src/ app/ tests/       # format
ruff check src/ app/ tests/  # lint
mypy src/                    # type check
Project Structure

research-scientist/
├── src/
│   ├── agents/       # LangGraph agents (Sprint 2+)
│   ├── clients/      # External API clients
│   ├── db/           # SQLAlchemy models + Alembic
│   ├── schemas/      # Pydantic schemas
│   ├── embeddings/   # FAISS vector search
│   ├── knowledge/    # NetworkX knowledge graph
│   ├── cache/        # TTL query cache
│   └── utils/        # Retry/logging utilities
├── app/              # Streamlit frontend
├── tests/
│   ├── unit/
│   └── integration/
├── data/             # SQLite DB, FAISS index (gitignored)
└── prompts/          # LLM prompts
Sprint Roadmap
Sprint	Focus	Deliverables
1	Foundations and Ingestion	DB, schemas, search clients, CI, Docker
2	Agents and Semantic Search	LangGraph pipeline, FAISS, Researcher/Extractor agents
3	Contradictions and Graph	FactChecker, Reasoning, Teacher, knowledge graph
4	Finalization and Demo	Memory, history, exports, testing, demo
Documentation
architecture.md — System design and key decisions

Sprint reports in docs/sprint-1/

Team
Khalil	Zeineb
Sprint 1	Repo/Docker/CI, arXiv client, Streamlit base	DB models, migrations, schemas, Brave client, docs
Sprint 2	LangGraph, Planner, FAISS, Streaming UI	Researcher Agent, Extractor Agent, SQLite storage
Sprint 3	FactChecker, Contradictions, Citations	Reasoning, Teacher, Knowledge Graph, Pyvis
Sprint 4	Memory, History, Exports	Final Response page, Tests, Documentation, Demo
