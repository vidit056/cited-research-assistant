# Cited Research Assistant (v1 MVP)

An **Agentic RAG System with Contradiction Detection & Self-Evaluation** built with Google Vertex AI (`gemini-3.7-flash` & `text-embedding-004`), FastAPI, SQLite, Chroma DB, and Streamlit.

---

## Key Features

1. **4-Step Functional Research Loop**:
   - **Step 1: Planning** — Decomposes complex research queries into 3–5 targeted sub-questions.
   - **Step 2: Retrieval & RAG Ingestion** — Queries Tavily search, scrapes clean text with `trafilatura`, chunks text, and indexes semantic embeddings into Chroma DB.
   - **Step 3: Grounded Synthesis** — Produces an authoritative Markdown report with inline `[n]` citations grounded strictly on retrieved chunks.
   - **Step 4: Citation Verification & Contradiction Detection** — Deterministically validates citations against raw text spans (using exact and `rapidfuzz` fuzzy matching) and flags cross-source conflicts.
2. **Zero-Infra SQLite Caching**:
   - SHA-256 keyed cache preserves Tavily search credits, ensures deterministic reproducibility during evaluations, and reduces latency.
3. **Audit Trail**:
   - Stores full raw texts, URL metadata, and exact `char_span` attributions in SQLite.
4. **First-Class Evaluation Harness**:
   - Built-in benchmark evaluation dataset with 15 questions, scoring Faithfulness, Citation Accuracy, and Retrieval Relevance.

---

## Quickstart Guide

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Key environment variables:
- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID
- `VERTEX_LOCATION`: Vertex region (e.g., `global` or `us-central1`)
- `TAVILY_API_KEY`: Your Tavily Search API key (optional for local mock/cache runs)

### 2. Start the FastAPI Backend
```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at: `http://localhost:8000/docs`

### 3. Start the Streamlit UI (Quick Launcher)
```bash
./run.sh
```
*(Or directly: `.venv/bin/streamlit run ui/streamlit_app.py --server.headless true`)*

### 4. Run the Evaluation Benchmark
```bash
./run_eval.sh 3
```

### 5. Run Automated Tests
```bash
PYTHONPATH=. .venv/bin/pytest -v
```
