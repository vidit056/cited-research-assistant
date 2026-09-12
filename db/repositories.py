import json
import hashlib
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy.orm import Session
from db.models import Run, Source, Citation, EvalScore, CacheEntry

def compute_cache_key(prefix: str, payload: str) -> str:
    """Computes a unique Search Cache Key (query/URL fingerprint) for caching search/scrape outputs."""
    raw = f"{prefix}:{payload.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def get_cache(session: Session, key: str) -> Optional[Any]:
    """Retrieves cached JSON object if present, else None."""
    entry = session.query(CacheEntry).filter(CacheEntry.key == key).first()
    if entry:
        try:
            return json.loads(entry.value)
        except Exception:
            return None
    return None

def set_cache(session: Session, key: str, provider: str, value: Any) -> None:
    """Saves or updates a cached JSON payload in SQLite."""
    serialized = json.dumps(value)
    existing = session.query(CacheEntry).filter(CacheEntry.key == key).first()
    if existing:
        existing.value = serialized
        existing.fetched_at = datetime.utcnow()
    else:
        new_entry = CacheEntry(
            key=key,
            provider=provider,
            value=serialized,
            fetched_at=datetime.utcnow()
        )
        session.add(new_entry)
    session.flush()

def create_run(session: Session, question: str, run_id: Optional[str] = None) -> Run:
    """Creates a new research run record."""
    run = Run(
        id=run_id or None,
        question=question,
        status="running",
        report_md="",
        sub_questions_json="[]",
        contradictions_json="[]"
    )
    session.add(run)
    session.flush()
    return run

def get_run(session: Session, run_id: str) -> Optional[Run]:
    """Fetches a run record by ID."""
    return session.query(Run).filter(Run.id == run_id).first()

def update_run(
    session: Session,
    run_id: str,
    status: str,
    report_md: str,
    sub_questions: List[str],
    contradictions: List[Dict[str, Any]]
) -> Optional[Run]:
    """Updates the final report and metadata for a run."""
    run = get_run(session, run_id)
    if run:
        run.status = status
        run.report_md = report_md
        run.sub_questions_json = json.dumps(sub_questions)
        run.contradictions_json = json.dumps(contradictions)
        session.flush()
    return run

def list_runs(session: Session, limit: int = 50) -> List[Run]:
    """Lists recent research runs ordered by created_at descending."""
    return session.query(Run).order_by(Run.created_at.desc()).limit(limit).all()

def save_sources(session: Session, run_id: str, sources: List[Dict[str, Any]]) -> List[Source]:
    """Persists extracted web sources for a run."""
    created_sources: List[Source] = []
    for s in sources:
        source_obj = Source(
            id=s.get("id"),
            run_id=run_id,
            url=s.get("url", ""),
            title=s.get("title", ""),
            domain=s.get("domain", ""),
            published_date=s.get("published_date"),
            raw_text=s.get("raw_text", ""),
            citation_num=s.get("citation_num", 1)
        )
        session.add(source_obj)
        created_sources.append(source_obj)
    session.flush()
    return created_sources

def get_sources_by_run(session: Session, run_id: str) -> List[Source]:
    """Retrieves all sources for a specific run."""
    return session.query(Source).filter(Source.run_id == run_id).order_by(Source.citation_num.asc()).all()

def save_citations(session: Session, run_id: str, citations: List[Dict[str, Any]]) -> List[Citation]:
    """Persists verified/unverified citation quotes and spans."""
    created_citations: List[Citation] = []
    for c in citations:
        span_str = ":".join(map(str, c.get("char_span", []))) if c.get("char_span") else ""
        cit_obj = Citation(
            id=c.get("id"),
            run_id=run_id,
            source_id=c.get("source_id"),
            quote=c.get("quote", ""),
            char_span=span_str,
            status=c.get("status", "verified")
        )
        session.add(cit_obj)
        created_citations.append(cit_obj)
    session.flush()
    return created_citations

def get_citations_by_run(session: Session, run_id: str) -> List[Citation]:
    """Retrieves all citations for a specific run."""
    return session.query(Citation).filter(Citation.run_id == run_id).all()

def save_eval_score(
    session: Session,
    run_id: str,
    faithfulness: float,
    citation_acc: float,
    retrieval_rel: float
) -> EvalScore:
    """Persists evaluation scores for a run."""
    score = EvalScore(
        run_id=run_id,
        faithfulness=faithfulness,
        citation_acc=citation_acc,
        retrieval_rel=retrieval_rel,
        created_at=datetime.utcnow()
    )
    session.add(score)
    session.flush()
    return score

def get_eval_scores_by_run(session: Session, run_id: str) -> List[EvalScore]:
    """Retrieves evaluation scores for a run."""
    return session.query(EvalScore).filter(EvalScore.run_id == run_id).all()
