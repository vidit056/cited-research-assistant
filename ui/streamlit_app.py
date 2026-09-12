import sys
import os
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from app.config import settings
from db.session import init_db, get_db_session
from db.repositories import list_runs, get_run, get_sources_by_run, get_citations_by_run
from agent.loop import execute_research_pipeline

# Ensure database is initialized
init_db()

st.set_page_config(
    page_title="Cited Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-verified {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-unverified {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .source-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .conflict-box {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🔬 Research Assistant")
    st.markdown("**Agentic RAG with Contradiction Detection**")
    st.divider()

    st.subheader("⚙️ Active Configuration")
    st.caption(f"**GCP Project:** `{settings.GOOGLE_CLOUD_PROJECT}`")
    st.caption(f"**Plan Model:** `{settings.MODEL_PLAN}`")
    st.caption(f"**Synth Model:** `{settings.MODEL_SYNTH}`")
    st.caption(f"**Verify Model:** `{settings.MODEL_VERIFY}`")
    st.caption(f"**Embeddings:** `{settings.EMBEDDING_MODEL}`")
    st.caption(f"**Search Key:** {'✅ Set' if settings.TAVILY_API_KEY else '⚠️ Not Set (Using Cache/Fallback)'}")

    st.divider()
    st.subheader("🕒 Previous Runs")

    with get_db_session() as session:
        db_runs = list_runs(session, limit=15)
        recent_runs = [
            {"id": r.id, "question": r.question, "status": r.status}
            for r in db_runs
        ]

    if recent_runs:
        for r in recent_runs:
            q_short = (r["question"][:35] + "...") if len(r["question"]) > 35 else r["question"]
            if st.button(f"📄 {q_short}", key=f"run_{r['id']}", use_container_width=True):
                st.session_state["selected_run_id"] = r["id"]
                st.session_state["current_result"] = None
    else:
        st.caption("No previous runs found.")

# Main Page Header
st.markdown("<div class='main-header'>Cited Research Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Verifiable, grounded multi-source research with deterministic quote checking and contradiction detection.</div>", unsafe_allow_html=True)

# Query Input Area
sample_prompts = [
    "Compare FastAPI vs Django for building AI and LLM service backends.",
    "How does LoRA reduce fine-tuning memory and compute costs for LLMs?",
    "What is the difference between HNSW and IVF-PQ indexing in vector databases?",
    "Explain FlashAttention and how it speeds up transformer self-attention computations."
]

selected_sample = st.selectbox(
    "💡 Or choose a benchmark sample query:",
    ["-- Select a sample prompt --"] + sample_prompts
)

default_query = selected_sample if selected_sample != "-- Select a sample prompt --" else ""
query = st.text_area(
    "Enter your research question:",
    value=default_query,
    height=80,
    placeholder="e.g. Compare FastAPI vs Django for building AI applications..."
)

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_clicked = st.button("🚀 Start Research", type="primary", use_container_width=True)

# Handle Execution
if run_clicked and query.strip():
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.info("🔄 Step 1/4: Decomposing question into targeted sub-questions...")
        progress_bar.progress(25)

        status_text.info("🌐 Step 2/4: Searching web, extracting clean text, and indexing into Chroma vector store...")
        progress_bar.progress(50)

        status_text.info("✍️ Step 3/4: Synthesizing grounded Markdown report with inline citations...")
        progress_bar.progress(75)

        status_text.info("🔍 Step 4/4: Performing verification pass and checking cross-source contradictions...")
        result = execute_research_pipeline(query.strip())
        progress_bar.progress(100)
        status_text.success("✅ Research complete!")

        st.session_state["current_result"] = result
        st.session_state["selected_run_id"] = result["run_id"]

    except Exception as e:
        status_text.error(f"❌ Research failed: {e}")

# Load Run Details from Session or DB
run_data = None
if st.session_state.get("current_result"):
    run_data = st.session_state["current_result"]
elif st.session_state.get("selected_run_id"):
    with get_db_session() as session:
        db_run = get_run(session, st.session_state["selected_run_id"])
        if db_run:
            db_sources = get_sources_by_run(session, db_run.id)
            db_citations = get_citations_by_run(session, db_run.id)
            source_cit_map = {s.id: s.citation_num for s in db_sources}
            import json
            run_data = {
                "run_id": db_run.id,
                "question": db_run.question,
                "status": db_run.status,
                "report_md": db_run.report_md,
                "sub_questions": json.loads(db_run.sub_questions_json) if db_run.sub_questions_json else [],
                "contradictions": json.loads(db_run.contradictions_json) if db_run.contradictions_json else [],
                "sources": [
                    {
                        "id": s.id,
                        "citation_num": s.citation_num,
                        "title": s.title,
                        "url": s.url,
                        "domain": s.domain,
                        "published_date": s.published_date,
                        "raw_text": s.raw_text
                    }
                    for s in db_sources
                ],
                "citations": [
                    {
                        "source_id": c.source_id,
                        "citation_num": source_cit_map.get(c.source_id, 1),
                        "quote": c.quote,
                        "char_span": [int(x) for x in c.char_span.split(":")] if c.char_span else [],
                        "status": c.status
                    }
                    for c in db_citations
                ]
            }

# Display Results
if run_data:
    st.divider()
    st.markdown(f"### 📋 Research for: *{run_data['question']}*")

    # Sub-questions pill tags
    if run_data.get("sub_questions"):
        st.markdown("**Sub-questions Investigated:**")
        cols = st.columns(len(run_data["sub_questions"]))
        for i, sq in enumerate(run_data["sub_questions"]):
            with cols[i]:
                st.info(f"**Q{i+1}:** {sq}")

    # Tabs
    tab_report, tab_sources, tab_conflicts, tab_citations = st.tabs([
        "📄 Research Report",
        f"📚 Sources ({len(run_data.get('sources', []))})",
        f"⚠️ Contradictions ({len(run_data.get('contradictions', []))})",
        f"🔍 Citation Verification ({len(run_data.get('citations', []))})"
    ])

    with tab_report:
        st.markdown(run_data.get("report_md", "*No report content available.*"))

    with tab_sources:
        sources = run_data.get("sources", [])
        if sources:
            for s in sources:
                with st.expander(f"[{s['citation_num']}] {s['title']} ({s['domain']})", expanded=False):
                    st.markdown(f"**URL:** [{s['url']}]({s['url']})")
                    if s.get("published_date"):
                        st.markdown(f"**Published Date:** `{s['published_date']}`")
                    st.markdown("**Raw Extracted Text:**")
                    st.text_area(
                        label="Full Text",
                        value=s["raw_text"],
                        height=200,
                        key=f"raw_text_{s['id']}"
                    )
        else:
            st.info("No sources recorded for this run.")

    with tab_conflicts:
        contradictions = run_data.get("contradictions", [])
        if contradictions:
            st.warning(f"Found {len(contradictions)} potential contradictions across sources:")
            for i, c in enumerate(contradictions):
                st.markdown(f"""
                <div class='conflict-box'>
                    <strong>Conflict #{i+1}:</strong> {c.get('explanation', '')}<br><br>
                    <strong>Source [{c.get('source_a_num', 1)}]:</strong> {c.get('claim_a', '')}<br>
                    <strong>Source [{c.get('source_b_num', 2)}]:</strong> {c.get('claim_b', '')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No conflicting claims or contradictions detected across sources.")

    with tab_citations:
        citations = run_data.get("citations", [])
        if citations:
            verified_count = sum(1 for c in citations if c.get("status") == "verified")
            unverified_count = len(citations) - verified_count
            acc_rate = round((verified_count / len(citations)) * 100, 1) if citations else 0

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Extracted Claims", len(citations))
            col_m2.metric("Verified Spans", verified_count)
            col_m3.metric("Citation Grounding Rate", f"{acc_rate}%")

            st.divider()
            for c in citations:
                is_ver = c.get("status") == "verified"
                badge = "<span class='badge-verified'>VERIFIED SPAN</span>" if is_ver else "<span class='badge-unverified'>UNVERIFIED</span>"
                span_text = f"Chars {c['char_span'][0]}-{c['char_span'][1]}" if c.get("char_span") else "No Span"

                st.markdown(f"""
                **Source [{c.get('citation_num', 1)}]** {badge} &nbsp; <code>{span_text}</code><br>
                > *"{c.get('quote', '')}"*
                """, unsafe_allow_html=True)
                st.write("")
        else:
            st.info("No citation claims verified yet.")
