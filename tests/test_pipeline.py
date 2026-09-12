import json
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from db.session import init_db, get_db_session
from db.repositories import (
    create_run,
    get_run,
    save_sources,
    get_sources_by_run,
    save_citations,
    get_citations_by_run,
    set_cache,
    get_cache,
    compute_cache_key
)
from agent.nodes import locate_quote_in_text
from app.main import app

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_config_per_step_knobs():
    """Verify per-step model knobs exist and default to gemini-3.7-flash."""
    assert settings.MODEL_PLAN == "gemini-3.7-flash"
    assert settings.MODEL_RETRIEVE == "gemini-3.7-flash"
    assert settings.MODEL_SYNTH == "gemini-3.7-flash"
    assert settings.MODEL_VERIFY == "gemini-3.7-flash"
    assert settings.EMBEDDING_MODEL == "text-embedding-004"

def test_eval_dataset_schema():
    """Verify test_dataset.json contains 15 benchmark questions with ground truth."""
    with open("eval/test_dataset.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 15, "Eval benchmark must contain exactly 15 questions"
    for item in data:
        assert "id" in item
        assert "question" in item and len(item["question"]) > 10
        assert "ground_truth" in item and len(item["ground_truth"]) > 10
        assert "must_cite_topics" in item and isinstance(item["must_cite_topics"], list)

def test_citation_span_matching_and_unverified():
    """Verify exact match, rapidfuzz fuzzy match, and unverified fallback."""
    raw_text = (
        "FastAPI is an asynchronous web framework built on Starlette and Pydantic. "
        "It provides high throughput and automatic interactive documentation with OpenAPI."
    )

    # 1. Exact match
    status1, span1 = locate_quote_in_text("asynchronous web framework built on Starlette", raw_text)
    assert status1 == "verified"
    assert raw_text[span1[0]:span1[1]] == "asynchronous web framework built on Starlette"

    # 2. Fuzzy match
    status2, span2 = locate_quote_in_text("provides high throughput and automatic OpenAPI docs", raw_text, threshold=75.0)
    assert status2 == "verified"
    assert len(span2) == 2

    # 3. Unverified when completely missing
    status3, span3 = locate_quote_in_text("Completely unrelated statement not in text", raw_text, threshold=85.0)
    assert status3 == "unverified"
    assert span3 == []

def test_cache_roundtrip_sha256():
    """Verify SHA-256 caching persists and retrieves identically."""
    with get_db_session() as session:
        cache_key = compute_cache_key("tavily", "test query for caching")
        payload = [{"title": "Cached Title", "url": "https://example.com", "snippet": "Sample"}]
        set_cache(session, cache_key, "tavily", payload)

        retrieved = get_cache(session, cache_key)
        assert retrieved == payload

def test_db_run_source_citation_persistence():
    """Verify persistence of Run, Source, and Citation records."""
    import uuid
    with get_db_session() as session:
        run = create_run(session, "What is Raft consensus?")
        run_id = run.id
        source_id = str(uuid.uuid4())
        citation_id = str(uuid.uuid4())

        sources = [
            {
                "id": source_id,
                "run_id": run_id,
                "url": "https://raft.github.io",
                "title": "Raft Consensus",
                "domain": "raft.github.io",
                "raw_text": "Raft is a consensus algorithm designed to be easy to understand.",
                "citation_num": 1
            }
        ]
        save_sources(session, run_id, sources)

        citations = [
            {
                "id": citation_id,
                "run_id": run_id,
                "source_id": source_id,
                "quote": "Raft is a consensus algorithm",
                "char_span": [0, 29],
                "status": "verified"
            }
        ]
        save_citations(session, run_id, citations)

        # Retrieve and verify
        saved_run = get_run(session, run_id)
        assert saved_run is not None
        assert saved_run.question == "What is Raft consensus?"

        saved_sources = get_sources_by_run(session, run_id)
        assert len(saved_sources) == 1
        assert saved_sources[0].url == "https://raft.github.io"

        saved_citations = get_citations_by_run(session, run_id)
        assert len(saved_citations) == 1
        assert saved_citations[0].status == "verified"
        assert saved_citations[0].char_span == "0:29"

def test_fastapi_endpoints():
    """Verify API health and listing endpoints."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}

    resp_list = client.get("/api/research")
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)
