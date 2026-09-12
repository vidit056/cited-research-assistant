# CITED RESEARCH ASSISTANT — PROJECT STATUS & ENGINEERING REPORT

**Project Name:** Cited Research Assistant  
**Author:** Vidit Jain  
**Document Version:** 1.0 (v1 MVP Complete)  
**Date:** September 2026  
**LLM & Embeddings Provider:** Google Vertex AI (`gemini-3.7-flash` & `text-embedding-004`)  
**Status:** v1 MVP Implemented, Verified, and Operational  

---

## 1. Executive Summary

The **Cited Research Assistant** is an agentic Retrieval-Augmented Generation (RAG) system designed to take natural-language research questions and produce **verifiable, cited Markdown reports**.

Unlike general-purpose chatbots that collapse research into a single opaque generation step without verifiable citations, this system makes the entire research lifecycle explicit:
1. **Plans sub-questions** to systematically decompose complex research topics.
2. **Retrieves live web sources** via the Tavily Search API and extracts clean content using `trafilatura`.
3. **Indexes and retrieves dense semantic chunks** using Google Vertex AI `text-embedding-004` and a local Chroma vector database.
4. **Synthesizes grounded Markdown prose** with inline `[n]` bracket citations matching retrieved chunks.
5. **Deterministically verifies citations** against raw source text using exact and fuzzy matching (`rapidfuzz`), marking unverified claims explicitly, and cross-checking sources for **factual contradictions**.
6. **Quantitatively self-evaluates** output against a fixed 15-question benchmark dataset across **Faithfulness**, **Citation Accuracy**, and **Retrieval Relevance**.

---

## 2. Actual Work Completed (Current State of the Project)

All items below have been implemented, integrated, tested, and verified in the codebase.

```
                      ┌────────────────────────────────────────┐
                      │          Streamlit Web UI              │
                      │  - Query input & live progress         │
                      │  - Cited Report & Collapsible Sources  │
                      │  - Contradiction & Verification viewer │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │          4-Step Agent Loop             │
                      │  (All powered by gemini-3.7-flash)     │
                      └───────────────────┬────────────────────┘
                                          │
       ┌──────────────────────┬───────────┴───────────┬──────────────────────┐
       ▼                      ▼                       ▼                      ▼
┌──────────────┐     ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ 1. Plan Node │     │ 2. Retrieve Node │    │3. Synthesizer   │    │ 4. Critic Node   │
│ - Decomposes │     │ - Tavily Search  │    │ - Markdown      │    │ - Fuzzy span     │
│   question   │     │ - Trafilatura    │    │   prose with    │    │   matching       │
│   into 3–5   │     │ - Chroma DB +    │    │   inline [n]    │    │ - Contradiction  │
│   sub-Qs     │     │   Vertex Embeds  │    │   citations     │    │   detection      │
└──────────────┘     └──────────────────┘    └─────────────────┘    └──────────────────┘
                              │                                              │
                              └──────────────────────┬───────────────────────┘
                                                     ▼
                                     ┌───────────────────────────────┐
                                     │   SQLite Database (.data/)    │
                                     │ - runs, sources, citations    │
                                     │ - eval_scores, cache_entries  │
                                     └───────────────────────────────┘
```

### 2.1 Virtual Environment & Configuration Layer
- **Isolated Virtualenv (`.venv`):** Standalone Python 3.14 virtual environment with all required dependencies installed (`google-genai`, `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `chromadb`, `tavily-python`, `trafilatura`, `httpx`, `rapidfuzz`, `streamlit`, `pytest`, `openpyxl`).
- **Per-Step Model Knobs (`app/config.py`):** Configured modular model knobs for all pipeline steps (`MODEL_PLAN`, `MODEL_RETRIEVE`, `MODEL_SYNTH`, `MODEL_VERIFY`), all defaulting to `gemini-3.7-flash` via Google Vertex AI.
- **Environment Management (`.env`, `.env.example`):** Managed environment secrets (`GOOGLE_CLOUD_PROJECT`, `VERTEX_LOCATION`, `TAVILY_API_KEY`, `DATABASE_URL`).
- **Authentication:** Verified live Google Cloud Vertex AI connection and Tavily Search API key authentication.

### 2.2 Evaluation Benchmark Dataset (`eval/test_dataset.json`)
- Authored **15 comprehensive benchmark research questions** with known-good reference answers (`ground_truth`) and required topic concepts (`must_cite_topics`).
- Domains covered:
  1. *FastAPI vs Django for AI Backends* (`q01`)
  2. *LoRA Fine-Tuning Memory Reduction* (`q02`)
  3. *HNSW vs IVF-PQ Vector Indexing* (`q03`)
  4. *FlashAttention Tiling Mechanisms* (`q04`)
  5. *RAG vs Long-Context LLMs* (`q05`)
  6. *AWQ vs GPTQ Quantization* (`q06`)
  7. *Raft Consensus & Log Replication* (`q07`)
  8. *Pydantic V2 Rust Rewrite* (`q08`)
  9. *gRPC vs REST for Microservices* (`q09`)
  10. *Cross-Encoder Re-Ranking Tradeoffs* (`q10`)
  11. *Speculative Decoding Latency Reduction* (`q11`)
  12. *OpenTelemetry for Distributed AI* (`q12`)
  13. *SQLite vs PostgreSQL in AI Agents* (`q13`)
  14. *Direct Preference Optimization (DPO) vs RLHF* (`q14`)
  15. *Hybrid Search (BM25 + Dense Vectors)* (`q15`)

### 2.3 Database Persistence Layer (`db/`)
- **SQLAlchemy Relational Schema (`db/models.py`):**
  - `runs`: Primary research run table (`id`, `question`, `status`, `report_md`, `sub_questions_json`, `contradictions_json`, `created_at`).
  - `sources`: Audit trail table persisting raw scraped articles (`id`, `run_id`, `url`, `title`, `domain`, `published_date`, `raw_text`, `citation_num`).
  - `citations`: Structured attribution table (`id`, `run_id`, `source_id`, `quote`, `char_span`, `status`).
  - `eval_scores`: Benchmark metric history table (`id`, `run_id`, `faithfulness`, `citation_acc`, `retrieval_rel`, `created_at`).
  - `cache_entries`: Table storing search and scrape payloads by query fingerprint.
- **Session Management (`db/session.py`):** SQLite engine configured at `.data/app.db` with `expire_on_commit=False` for thread-safe ORM access across UI and background threads.
- **CRUD Repositories (`db/repositories.py`):** Modular helper functions isolating database operations from agent logic.

### 2.4 Search Cache Key Mechanism
- Implemented a query/URL fingerprint cache (`compute_cache_key`) that saves Tavily search responses and `trafilatura` web page extractions into SQLite.
- **Impact:** Prevents redundant web requests, saves Tavily API credits, eliminates unnecessary network latency, and ensures deterministic evaluation runs.

### 2.5 Web Tools & RAG Engine (`tools/`, `rag/`)
- **Web Search Tool (`tools/web_search.py`):** Tavily search API client with cache lookup and automatic fallback.
- **Web Scraper Tool (`tools/scraper.py`):** Robust `httpx` downloader and `trafilatura` article extractor that strips ads, headers, and navigation menus.
- **Text Chunker (`rag/ingest.py`):** Splits source texts into sentence-aware ~800 character chunks with 150-character overlap with full provenance metadata.
- **Embeddings Wrapper (`rag/embeddings.py`):** Google Vertex AI `text-embedding-004` client generating 768-dimensional dense vectors in batches.
- **Vector Store (`rag/vectorstore.py`):** Manages local Chroma DB collections per research run, supporting cosine similarity semantic search.

### 2.6 The 4-Step Hand-Rolled Agent Loop (`agent/`)
- **Prompts (`agent/prompts.py`):** Specialized system prompts enforcing strict citation formatting, claim extraction, and contradiction checks.
- **Pipeline Nodes (`agent/nodes.py`):**
  - `plan_node`: Decomposes input questions into 3–5 targeted sub-questions using `gemini-3.7-flash`.
  - `retrieve_node`: Gathers live web sources, indexes them into Chroma DB, and retrieves top-$k$ relevant chunks per sub-question.
  - `synthesize_node`: Synthesizes an authoritative Markdown report with inline `[n]` bracket citations strictly grounded on retrieved excerpts.
  - `verify_node`: Verifies quotes against `sources.raw_text` using exact matching and `rapidfuzz.fuzz.partial_ratio` (threshold: 85%). Assigns exact `char_span` indices (`[start, end]`) and marks unverified claims as `unverified` (never faking spans). Identifies cross-source contradictions.
- **Loop Orchestrator (`agent/loop.py`):** Coordinates the execution, cleans up ephemeral Chroma collections, and persists runs, sources, and citations to SQLite.

### 2.7 Application Interfaces (Backend & Frontend)
- **FastAPI REST API (`app/main.py`, `app/routes/research.py`):**
  - `POST /api/research`: Submits a research question and returns the full report with sources and citations.
  - `GET /api/research/{run_id}`: Fetches stored results for a specific run.
  - `GET /api/research`: Lists historical research runs.
  - `GET /health`: Health check endpoint.
  - Interactive Swagger documentation at `http://localhost:8000/docs`.
- **Streamlit Web UI (`ui/streamlit_app.py`):**
  - Visual interface accessible at `http://localhost:8501`.
  - Step-by-step progress visualizer across the 4 stages.
  - **Research Report Tab:** Formatted Markdown report with inline citations.
  - **Sources Tab:** Collapsible cards showing titles, URLs, domains, and full raw text.
  - **Contradictions Tab:** Warning callout cards displaying conflicting claims across sources.
  - **Citation Verification Tab:** Metric dashboard showing Grounding Rate % and character spans.

### 2.8 Evaluation Scorer Harness (`eval/run_eval.py`)
- Automated benchmark runner that evaluates research runs against `test_dataset.json` and computes:
  1. **Citation Accuracy (0–100%):** Deterministic verification of citations resolving to real source spans.
  2. **Faithfulness (0.0–1.0):** LLM-as-a-judge score measuring factual grounding against sources.
  3. **Retrieval Relevance (0.0–1.0):** Evaluates coverage of required `must_cite_topics`.
- Automatically logs all scores to the database `eval_scores` table.

### 2.9 Testing & Spreadsheets
- **Pytest Suite (`tests/test_pipeline.py`):** 6 automated unit and integration tests verifying config knobs, dataset schemas, fuzzy matching, cache roundtrips, database persistence, and API endpoints (100% passing).
- **Spreadsheet Tracking (`PROJECT_LOG.xlsx` & CSVs):** Structured work log in `docs/` detailing tasks, architecture, and bug resolutions.

---

## 3. Issues Encountered, Root Causes & Fixes Applied

| Issue ID | Component | Symptom / Error | Root Cause Analysis | Fix Applied | Status |
|---|---|---|---|---|---|
| **ISS-01** | Python Venv | `python3 -m venv` failed with missing `ensurepip` | Debian/Ubuntu Linux Python 3.14 on WSL lacked `python3-venv` package. | Created virtualenv with `--without-pip` and bootstrapped pip using `get-pip.py`. | **Resolved** |
| **ISS-02** | Test Suite | `pytest` failed with `ModuleNotFoundError: No module named 'app'` | Pytest was invoked from `tests/` without the workspace root directory in Python's `sys.path`. | Added `tests/conftest.py` setting `sys.path.insert(0, ROOT_DIR)` and `PYTHONPATH=.`. | **Resolved** |
| **ISS-03** | Streamlit UI | Terminal paused at `Email: |` prompt | Streamlit prompts for optional newsletter registration on fresh installs in non-headless mode. | Pressed Enter to skip, and documented `--server.headless true`. | **Resolved** |
| **ISS-04** | Network / Browser | `ERR_SSL_PROTOCOL_ERROR` & `Invalid HTTP request` | Chrome automatically redirected `localhost:8501` to `https://` instead of plain `http://`. | Accessed using explicit `http://localhost:8501` or `http://127.0.0.1:8501` in Incognito. | **Resolved** |
| **ISS-05** | Database / UI | `DetachedInstanceError: Instance <Run> is not bound to a Session` | SQLAlchemy expired ORM object attributes on `session.close()`, causing sidebar buttons to fail. | Configured `expire_on_commit=False` in `db/session.py` and extracted dictionary values in `ui/streamlit_app.py`. | **Resolved** |

---

## 4. Technology Stack & Current Configuration

| Layer / Parameter | Technology | Configuration Value | Purpose |
|---|---|---|---|
| **Primary LLM** | Google Vertex AI | `gemini-3.7-flash` | Powers Planning, Retrieval Reasoning, Synthesis, and Verification |
| **Embeddings** | Google Vertex AI | `text-embedding-004` | 768-dimensional dense vector embeddings |
| **Search Engine** | Tavily Search API | `TAVILY_API_KEY` | Live web search and ranked URL discovery |
| **Extraction** | `trafilatura` + `httpx` | Timeout: 12.0s | HTML article text and metadata extraction |
| **Vector DB** | Chroma DB | `.data/chroma` | Local cosine similarity vector index per run |
| **Persistence** | SQLite / SQLAlchemy | `.data/app.db` | Stores runs, sources, citations, eval scores, and cache |
| **Caching** | Search Cache Key | SQLite Keyed Table | Query/URL fingerprint cache preserving API credits |
| **Citation Matcher** | `rapidfuzz` | Threshold = 85.0% | Verifies quotes to exact character spans in raw source text |
| **Backend API** | FastAPI + Uvicorn | Port 8000 | REST API endpoints for research task management |
| **Frontend UI** | Streamlit | Port 8501 | Interactive research dashboard |

---

## 5. Future Roadmap & Planned Phases

### Phase 2: Trust & Retrieval Quality (v2)
- **Cross-Encoder Re-Ranking (`FlashRank`):** Add a local cross-encoder re-ranker to prune lower-quality chunks from the top 20 candidate pool before passing to Gemini.
- **Hybrid Search (Dense + BM25):** Combine semantic vector search with sparse keyword search (BM25) using Reciprocal Rank Fusion (RRF) to capture exact acronyms, names, and error codes.
- **PDF & Document Ingestion:** Allow users to upload local PDF research papers directly into the Chroma vector store.
- **Observability:** Integrate Langfuse / OpenTelemetry tracing for per-step latency and token cost analysis.

### Phase 3: Productization & Scaling (v3)
- **Asynchronous Task Workers:** Implement Celery / Redis background worker queues for non-blocking research execution.
- **Real-Time Token Streaming:** Add Server-Sent Events (SSE) or WebSockets to stream intermediate reasoning steps and report prose in real time.
- **Report Exporting:** Export cited reports to formatted PDF, Word, and Notion.
- **Multi-Agent Process Separation:** Promote Python functional nodes into independent specialized workers if system scale demands it.

### Phase 4: Production Deployment (v4)
- **Dockerization:** Provide `Dockerfile` and `docker-compose.yml` for reproducible single-command deployments.
- **PostgreSQL Migration:** Move from local SQLite to managed PostgreSQL with `pgvector` for multi-user production environments.

---

## 6. How to Run the Application

### 1. Launch Streamlit Web UI
```bash
cd /home/vidit/research-assistant
.venv/bin/streamlit run ui/streamlit_app.py --server.headless true --server.port 8501
```
Open in browser: `http://localhost:8501`

### 2. Launch FastAPI REST Backend
```bash
cd /home/vidit/research-assistant
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open Swagger docs: `http://localhost:8000/docs`

### 3. Run Evaluation Benchmark
```bash
cd /home/vidit/research-assistant
PYTHONPATH=. .venv/bin/python3 eval/run_eval.py --limit 3
```

### 4. Run Pytest Suite
```bash
cd /home/vidit/research-assistant
PYTHONPATH=. .venv/bin/pytest -v
```
