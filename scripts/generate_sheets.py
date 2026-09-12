import os
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Sheet 1: Tasks & Scope Tracker
tasks_data = [
    {
        "Task / Feature": "Environment & Model Knobs",
        "Category": "Core Config",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": ".env.example, .env, app/config.py with per-step model knobs (all default to gemini-3.7-flash)"
    },
    {
        "Task / Feature": "Evaluation Benchmark Dataset",
        "Category": "Evaluation",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "eval/test_dataset.json (15 benchmark questions with ground truth & must-cite topics)"
    },
    {
        "Task / Feature": "Database Schema & Persistence",
        "Category": "Database",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "db/models.py, db/session.py, db/repositories.py (SQLite/Postgres: runs, sources, citations, eval_scores)"
    },
    {
        "Task / Feature": "Search Cache Key Mechanism",
        "Category": "Caching",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "db/repositories.py compute_cache_key() (Query/URL fingerprinting to save API credits & ensure reproducibility)"
    },
    {
        "Task / Feature": "Web Search & Scraping Tools",
        "Category": "Tools",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "tools/web_search.py (Tavily API) and tools/scraper.py (trafilatura clean text extractor)"
    },
    {
        "Task / Feature": "Document Chunking & Provenance",
        "Category": "RAG Core",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "rag/ingest.py (Sentence-boundary chunking ~800 chars, 150 overlap with source metadata)"
    },
    {
        "Task / Feature": "Vertex AI Semantic Embeddings",
        "Category": "RAG Core",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "rag/embeddings.py (Google Vertex AI text-embedding-004 768-dim vector embeddings)"
    },
    {
        "Task / Feature": "Chroma Vector Store",
        "Category": "RAG Core",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "rag/vectorstore.py (Local Chroma DB collection indexing & cosine similarity retrieval)"
    },
    {
        "Task / Feature": "4-Step Agent Loop & Prompts",
        "Category": "Agent Loop",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "agent/prompts.py, agent/nodes.py, agent/loop.py (Plan -> Retrieve -> Synthesize -> Verify)"
    },
    {
        "Task / Feature": "Fuzzy Citation Span Verification",
        "Category": "Verification",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "agent/nodes.py locate_quote_in_text() (Exact match + rapidfuzz with unverified fallback)"
    },
    {
        "Task / Feature": "FastAPI REST API Service",
        "Category": "Backend",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "app/main.py, app/routes/research.py (REST endpoints: /api/research submit & fetch, /health, Swagger docs)"
    },
    {
        "Task / Feature": "Streamlit Web Interface",
        "Category": "Frontend UI",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "ui/streamlit_app.py (4-step progress visualizer, cited Markdown viewer, sources explorer, conflict alerts)"
    },
    {
        "Task / Feature": "Evaluation Scorer & Benchmarking",
        "Category": "Evaluation",
        "Version": "v1 MVP",
        "Status": "Completed",
        "Implementation Details / Files": "eval/run_eval.py (Measures Faithfulness, Citation Accuracy, and Retrieval Relevance against benchmark)"
    },
    {
        "Task / Feature": "Cross-Encoder Re-Ranking",
        "Category": "RAG Advanced",
        "Version": "v2 Roadmap",
        "Status": "Deferred",
        "Implementation Details / Files": "FlashRank re-ranking candidate pool to improve Top-K precision"
    },
    {
        "Task / Feature": "Hybrid Search (Dense + BM25)",
        "Category": "RAG Advanced",
        "Version": "v2 Roadmap",
        "Status": "Deferred",
        "Implementation Details / Files": "Combining sparse lexical matching with dense vector retrieval using RRF"
    },
    {
        "Task / Feature": "Async Worker Queues & SSE Streaming",
        "Category": "Architecture",
        "Version": "v3 Roadmap",
        "Status": "Deferred",
        "Implementation Details / Files": "Celery/Redis background worker queue with real-time Server-Sent Events"
    }
]

# Sheet 2: Issues, Root Causes & Fixes Log
issues_data = [
    {
        "Issue ID": "ISS-01",
        "Component": "Environment Setup",
        "Symptom / Error": "python3 -m venv failed due to missing ensurepip",
        "Root Cause Analysis": "Debian/Ubuntu Linux Python 3.14 on WSL did not have the python3-venv package installed.",
        "Fix Applied": "Created virtual environment with --without-pip and bootstrapped standalone pip using get-pip.py.",
        "Status": "Resolved"
    },
    {
        "Issue ID": "ISS-02",
        "Component": "Test Harness",
        "Symptom / Error": "pytest failed with ModuleNotFoundError: No module named 'app'",
        "Root Cause Analysis": "pytest was invoked from inside the tests/ directory without the workspace root directory added to Python's module search path (sys.path).",
        "Fix Applied": "Added tests/conftest.py to insert project root into sys.path and set PYTHONPATH=..",
        "Status": "Resolved"
    },
    {
        "Issue ID": "ISS-03",
        "Component": "Streamlit UI",
        "Symptom / Error": "Terminal hung at 'Email: |' and refused connections",
        "Root Cause Analysis": "Streamlit prompts for optional newsletter registration on fresh installations when not run in headless mode.",
        "Fix Applied": "Skipped prompt by pressing Enter, and documented using --server.headless true for headless execution.",
        "Status": "Resolved"
    },
    {
        "Issue ID": "ISS-04",
        "Component": "Network / Browser",
        "Symptom / Error": "Browser showed ERR_SSL_PROTOCOL_ERROR and terminal logged 'Invalid HTTP request'",
        "Root Cause Analysis": "Google Chrome automatically redirected localhost:8501 to https:// (SSL), but Streamlit runs as a plain HTTP server.",
        "Fix Applied": "Accessed the application using explicit http://localhost:8501 or http://127.0.0.1:8501 in an Incognito tab.",
        "Status": "Resolved"
    },
    {
        "Issue ID": "ISS-05",
        "Component": "Database / Streamlit",
        "Symptom / Error": "sqlalchemy.orm.exc.DetachedInstanceError: Instance <Run> is not bound to a Session",
        "Root Cause Analysis": "SQLAlchemy expired ORM object attributes upon session.close(), causing attribute access on sidebar buttons to fail outside the active session.",
        "Fix Applied": "Configured expire_on_commit=False in db/session.py and extracted dictionary values inside the session block in ui/streamlit_app.py.",
        "Status": "Resolved"
    }
]

# Sheet 3: System Architecture & Config
arch_data = [
    {
        "Layer / Component": "Primary LLM Reasoning",
        "Technology / Parameter": "Google Vertex AI (gemini-3.7-flash)",
        "Current Value / Configuration": "MODEL_PLAN / MODEL_RETRIEVE / MODEL_SYNTH / MODEL_VERIFY",
        "Role & Purpose in v1 MVP": "Handles sub-question planning, grounded report writing, and citation/contradiction checking."
    },
    {
        "Layer / Component": "Vector Embeddings Model",
        "Technology / Parameter": "Google Vertex AI (text-embedding-004)",
        "Current Value / Configuration": "768-dimensional float vectors",
        "Role & Purpose in v1 MVP": "Converts scraped document chunks and sub-question queries into semantic dense vectors."
    },
    {
        "Layer / Component": "Vector Database",
        "Technology / Parameter": "Chroma DB",
        "Current Value / Configuration": ".data/chroma (Local persistent storage)",
        "Role & Purpose in v1 MVP": "Indexes document chunks per research session and performs cosine similarity search."
    },
    {
        "Layer / Component": "Persistent Database",
        "Technology / Parameter": "SQLite (SQLAlchemy ORM)",
        "Current Value / Configuration": ".data/app.db (PostgreSQL ready via DATABASE_URL)",
        "Role & Purpose in v1 MVP": "Persists research runs, source URLs, citation character spans, and eval benchmark scores."
    },
    {
        "Layer / Component": "Search Cache Key",
        "Technology / Parameter": "Query/URL Fingerprint in SQLite",
        "Current Value / Configuration": "Cache table in app.db",
        "Role & Purpose in v1 MVP": "Caches Tavily search responses and trafilatura extractions to save API quota & ensure reproducibility."
    },
    {
        "Layer / Component": "Web Search Provider",
        "Technology / Parameter": "Tavily Search API",
        "Current Value / Configuration": "TAVILY_API_KEY (.env)",
        "Role & Purpose in v1 MVP": "Executes live web searches and returns ranked results and snippets."
    },
    {
        "Layer / Component": "Web Scraper",
        "Technology / Parameter": "trafilatura + httpx",
        "Current Value / Configuration": "trafilatura v2.2.0 (Timeout: 12s)",
        "Role & Purpose in v1 MVP": "Downloads web pages and strips boilerplate/ads to extract clean readable text."
    },
    {
        "Layer / Component": "Citation Verification",
        "Technology / Parameter": "rapidfuzz Partial Ratio",
        "Current Value / Configuration": "CITATION_MATCH_THRESHOLD = 85.0",
        "Role & Purpose in v1 MVP": "Locates verbatim quoted claims in raw source text; marks as unverified if match fails."
    },
    {
        "Layer / Component": "Backend API",
        "Technology / Parameter": "FastAPI + Uvicorn",
        "Current Value / Configuration": "Port 8000 (Swagger docs at /docs)",
        "Role & Purpose in v1 MVP": "Provides REST API endpoints for submitting research queries and fetching run history."
    },
    {
        "Layer / Component": "Frontend User Interface",
        "Technology / Parameter": "Streamlit",
        "Current Value / Configuration": "Port 8501 (ui/streamlit_app.py)",
        "Role & Purpose in v1 MVP": "Provides interactive dashboard with 4-step progress, cited report, and conflict alerts."
    }
]

# Convert to DataFrames
df_tasks = pd.DataFrame(tasks_data)
df_issues = pd.DataFrame(issues_data)
df_arch = pd.DataFrame(arch_data)

# 1. Save Excel Workbook with multiple sheets
excel_path = ROOT_DIR / "PROJECT_LOG.xlsx"
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    df_tasks.to_excel(writer, sheet_name="Tasks & Scope", index=False)
    df_issues.to_excel(writer, sheet_name="Issues & Bug Log", index=False)
    df_arch.to_excel(writer, sheet_name="Architecture & Config", index=False)

# 2. Save individual CSV files for easy import to Google Sheets
df_tasks.to_csv(DOCS_DIR / "tasks_and_scope.csv", index=False)
df_issues.to_csv(DOCS_DIR / "issues_and_resolutions_log.csv", index=False)
df_arch.to_csv(DOCS_DIR / "system_architecture.csv", index=False)

print(f"✅ Generated Excel sheet at: {excel_path}")
print(f"✅ Generated CSV files at: {DOCS_DIR}")
