import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from db.session import get_db_session
from db.repositories import (
    create_run,
    get_run,
    update_run,
    save_sources,
    save_citations
)
from agent.nodes import plan_node, retrieve_node, synthesize_node, verify_node
from rag.vectorstore import vector_store

def execute_research_pipeline(question: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the 4-step research loop:
    1. Plan -> 2. Retrieve & RAG Index -> 3. Grounded Synthesis -> 4. Verifiable Attribution & Contradictions.
    Persists all artifacts into SQLite database.
    """
    if not run_id:
        run_id = str(uuid.uuid4())

    with get_db_session() as session:
        create_run(session, question=question, run_id=run_id)

    try:
        # Step 1: Plan
        print(f"[Agent Loop] Step 1/4: Planning sub-questions for '{question}'...")
        sub_questions = plan_node(question)

        # Step 2: Retrieve & Ingest (RAG)
        print(f"[Agent Loop] Step 2/4: Searching and retrieving sources for {len(sub_questions)} sub-questions...")
        sources, retrieved_chunks = retrieve_node(run_id, question, sub_questions)

        with get_db_session() as session:
            save_sources(session, run_id, sources)

        # Step 3: Grounded Synthesis
        print(f"[Agent Loop] Step 3/4: Synthesizing cited report with Gemini ({len(retrieved_chunks)} chunks)...")
        report_md = synthesize_node(question, sub_questions, retrieved_chunks, sources)

        # Step 4: Citation Verification & Contradiction Detection
        print(f"[Agent Loop] Step 4/4: Verifying citation spans and checking contradictions...")
        citations, contradictions = verify_node(report_md, sources)

        with get_db_session() as session:
            save_citations(session, run_id, citations)
            update_run(
                session=session,
                run_id=run_id,
                status="completed",
                report_md=report_md,
                sub_questions=sub_questions,
                contradictions=contradictions
            )

        # Cleanup ephemeral Chroma collection
        vector_store.delete_run_collection(run_id)

        return {
            "run_id": run_id,
            "question": question,
            "status": "completed",
            "report_md": report_md,
            "sub_questions": sub_questions,
            "sources": sources,
            "citations": citations,
            "contradictions": contradictions,
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        print(f"[Agent Loop] Error executing pipeline for run {run_id}: {e}")
        with get_db_session() as session:
            update_run(
                session=session,
                run_id=run_id,
                status="failed",
                report_md=f"**Error occurred during research execution:** {str(e)}",
                sub_questions=[],
                contradictions=[]
            )
        raise
