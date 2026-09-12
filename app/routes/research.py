import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import (
    ResearchRequest,
    ResearchResponse,
    SourceItem,
    CitationItem,
    ContradictionItem
)
from db.session import get_db
from db.repositories import (
    get_run,
    list_runs,
    get_sources_by_run,
    get_citations_by_run
)
from agent.loop import execute_research_pipeline

router = APIRouter(prefix="/api/research", tags=["research"])

@router.post("", response_model=ResearchResponse, status_code=status.HTTP_200_OK)
def submit_research_task(request: ResearchRequest):
    """
    Executes the 4-step research loop synchronously for a given research question.
    Returns the cited Markdown report, sources, citations, and detected contradictions.
    """
    try:
        result = execute_research_pipeline(question=request.question)
        return ResearchResponse(
            run_id=result["run_id"],
            question=result["question"],
            status=result["status"],
            report_md=result["report_md"],
            sub_questions=result.get("sub_questions", []),
            sources=[
                SourceItem(
                    id=s["id"],
                    citation_num=s["citation_num"],
                    title=s["title"],
                    url=s["url"],
                    domain=s["domain"],
                    published_date=s.get("published_date"),
                    raw_text=s["raw_text"]
                )
                for s in result.get("sources", [])
            ],
            citations=[
                CitationItem(
                    source_id=c["source_id"],
                    citation_num=c["citation_num"],
                    quote=c["quote"],
                    char_span=c.get("char_span", []),
                    status=c.get("status", "verified")
                )
                for c in result.get("citations", [])
            ],
            contradictions=[
                ContradictionItem(
                    claim_a=con["claim_a"],
                    source_a_num=con["source_a_num"],
                    claim_b=con["claim_b"],
                    source_b_num=con["source_b_num"],
                    explanation=con["explanation"]
                )
                for con in result.get("contradictions", [])
            ],
            created_at=result["created_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research pipeline execution failed: {str(e)}"
        )

@router.get("/{run_id}", response_model=ResearchResponse)
def get_research_run(run_id: str, session: Session = Depends(get_db)):
    """
    Retrieves stored research results, citations, and sources for a previous run.
    """
    run = get_run(session, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research run with ID '{run_id}' not found."
        )

    sources = get_sources_by_run(session, run_id)
    citations = get_citations_by_run(session, run_id)

    sub_questions = []
    try:
        sub_questions = json.loads(run.sub_questions_json)
    except Exception:
        pass

    contradictions = []
    try:
        contradictions = json.loads(run.contradictions_json)
    except Exception:
        pass

    return ResearchResponse(
        run_id=run.id,
        question=run.question,
        status=run.status,
        report_md=run.report_md,
        sub_questions=sub_questions,
        sources=[
            SourceItem(
                id=s.id,
                citation_num=s.citation_num,
                title=s.title,
                url=s.url,
                domain=s.domain,
                published_date=s.published_date,
                raw_text=s.raw_text
            )
            for s in sources
        ],
        citations=[
            CitationItem(
                source_id=c.source_id,
                citation_num=c.source.citation_num if c.source else 1,
                quote=c.quote,
                char_span=[int(x) for x in c.char_span.split(":")] if c.char_span else [],
                status=c.status
            )
            for c in citations
        ],
        contradictions=[
            ContradictionItem(
                claim_a=con.get("claim_a", ""),
                source_a_num=con.get("source_a_num", 1),
                claim_b=con.get("claim_b", ""),
                source_b_num=con.get("source_b_num", 2),
                explanation=con.get("explanation", "")
            )
            for con in contradictions
        ],
        created_at=run.created_at.isoformat()
    )

@router.get("", response_model=List[ResearchResponse])
def list_research_runs(limit: int = 20, session: Session = Depends(get_db)):
    """Lists recent research runs."""
    runs = list_runs(session, limit=limit)
    response_list = []
    for r in runs:
        sources = get_sources_by_run(session, r.id)
        citations = get_citations_by_run(session, r.id)
        sub_questions = json.loads(r.sub_questions_json) if r.sub_questions_json else []
        contradictions = json.loads(r.contradictions_json) if r.contradictions_json else []

        response_list.append(
            ResearchResponse(
                run_id=r.id,
                question=r.question,
                status=r.status,
                report_md=r.report_md,
                sub_questions=sub_questions,
                sources=[
                    SourceItem(
                        id=s.id,
                        citation_num=s.citation_num,
                        title=s.title,
                        url=s.url,
                        domain=s.domain,
                        published_date=s.published_date,
                        raw_text=s.raw_text
                    )
                    for s in sources
                ],
                citations=[
                    CitationItem(
                        source_id=c.source_id,
                        citation_num=c.source.citation_num if c.source else 1,
                        quote=c.quote,
                        char_span=[int(x) for x in c.char_span.split(":")] if c.char_span else [],
                        status=c.status
                    )
                    for c in citations
                ],
                contradictions=[
                    ContradictionItem(
                        claim_a=con.get("claim_a", ""),
                        source_a_num=con.get("source_a_num", 1),
                        claim_b=con.get("claim_b", ""),
                        source_b_num=con.get("source_b_num", 2),
                        explanation=con.get("explanation", "")
                    )
                    for con in contradictions
                ],
                created_at=r.created_at.isoformat()
            )
        )
    return response_list
