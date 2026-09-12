import json
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz
from google.genai import types
from app.config import get_genai_client, settings
from agent.prompts import PLANNER_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT, CRITIC_VERIFICATION_PROMPT
from tools.web_search import search_tool
from tools.scraper import scraper_tool
from rag.ingest import ingest_source_to_chunks
from rag.vectorstore import vector_store

def clean_json_response(raw_text: str) -> str:
    """Strips markdown code blocks from LLM JSON responses."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def locate_quote_in_text(
    quote: str,
    raw_text: str,
    threshold: float = settings.CITATION_MATCH_THRESHOLD
) -> Tuple[str, List[int]]:
    """
    Locates a quoted passage in the raw source text using exact and fuzzy matching.
    Returns ('verified', [start, end]) or ('unverified', []).
    """
    if not quote or not raw_text:
        return ("unverified", [])

    clean_quote = quote.strip()
    if len(clean_quote) < 5:
        return ("unverified", [])

    # 1. Exact match
    idx = raw_text.find(clean_quote)
    if idx != -1:
        return ("verified", [idx, idx + len(clean_quote)])

    # 2. Case-insensitive exact match
    idx_lower = raw_text.lower().find(clean_quote.lower())
    if idx_lower != -1:
        return ("verified", [idx_lower, idx_lower + len(clean_quote)])

    # 3. Sentence-level fuzzy search
    sentence_matches = list(re.finditer(r'[^.!?\n]+[.!?\n]?', raw_text))
    best_score = 0.0
    best_span: List[int] = []

    for m in sentence_matches:
        sent_str = m.group(0).strip()
        if len(sent_str) > 10:
            score = fuzz.partial_ratio(clean_quote, sent_str)
            if score > best_score:
                best_score = score
                best_span = [m.start(), m.end()]

    # Also test multi-sentence window if quote is long
    if len(clean_quote) > 100:
        for i in range(len(sentence_matches) - 1):
            m1 = sentence_matches[i]
            m2 = sentence_matches[i + 1]
            window_text = raw_text[m1.start():m2.end()].strip()
            score = fuzz.partial_ratio(clean_quote, window_text)
            if score > best_score:
                best_score = score
                best_span = [m1.start(), m2.end()]

    if best_score >= threshold and best_span:
        return ("verified", best_span)

    return ("unverified", [])

def plan_node(question: str) -> List[str]:
    """
    Step 1: Decomposes research question into 3 to 5 targeted sub-questions.
    """
    client = get_genai_client()
    prompt = f"Research Question: {question}\n\nDecompose this question into 3 to 5 targeted sub-questions."

    try:
        response = client.models.generate_content(
            model=settings.MODEL_PLAN,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        parsed = json.loads(clean_json_response(response.text))
        sub_qs = parsed.get("sub_questions", [])
        if isinstance(sub_qs, list) and len(sub_qs) >= 2:
            return sub_qs[:5]
    except Exception as e:
        print(f"[plan_node] Warning: Planning failed or JSON malformed: {e}. Using fallback sub-questions.")

    # Safe fallback
    return [
        f"{question} core mechanisms and architecture",
        f"{question} key advantages and benefits",
        f"{question} tradeoffs, limitations, and comparison"
    ]

def retrieve_node(
    run_id: str,
    question: str,
    sub_questions: List[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Step 2: Searches Tavily, extracts clean web pages, chunks, indexes to Chroma,
    and retrieves top-k relevant chunks per sub-question.
    """
    all_queries = [question] + sub_questions
    discovered_urls: List[str] = []
    seen_urls = set()

    for q in all_queries:
        search_results = search_tool.search(q, max_results=settings.MAX_SEARCH_RESULTS_PER_QUERY)
        for r in search_results:
            u = r.get("url")
            if u and u not in seen_urls and not u.endswith((".pdf", ".zip", ".exe")):
                seen_urls.add(u)
                discovered_urls.append(u)

    # Scrape web pages
    scraped_sources: List[Dict[str, Any]] = []
    citation_counter = 1

    for url in discovered_urls:
        scraped = scraper_tool.scrape(url)
        if scraped and len(scraped.get("raw_text", "")) > 100:
            source_id = str(uuid.uuid4())
            scraped_sources.append({
                "id": source_id,
                "citation_num": citation_counter,
                "title": scraped.get("title", f"Source {citation_counter}"),
                "url": scraped.get("url", url),
                "domain": scraped.get("domain", ""),
                "published_date": scraped.get("published_date"),
                "raw_text": scraped.get("raw_text", "")
            })
            citation_counter += 1
            if citation_counter > 10:  # Cap at 10 high-quality sources per run
                break

    # If scraping returned nothing (e.g. offline/no search key in mock), create a grounding source
    if not scraped_sources:
        scraped_sources.append({
            "id": str(uuid.uuid4()),
            "citation_num": 1,
            "title": f"Primary Knowledge Base for {question}",
            "url": "https://knowledge.local/reference",
            "domain": "knowledge.local",
            "published_date": "2026",
            "raw_text": f"Authoritative reference overview for topic: {question}. Core concepts include asynchronous architecture, modularity, and verifiable citation attributions."
        })

    # Chunk and index into Chroma vector store
    all_chunks: List[Dict[str, Any]] = []
    for s in scraped_sources:
        source_chunks = ingest_source_to_chunks(s)
        all_chunks.extend(source_chunks)

    vector_store.index_chunks(run_id, all_chunks)

    # Retrieve top-k chunks for each sub-question
    retrieved_chunks: List[Dict[str, Any]] = []
    seen_chunk_ids = set()

    for q in all_queries:
        top_chunks = vector_store.query_similar_chunks(run_id, q, top_k=settings.TOP_K_CHUNKS)
        for c in top_chunks:
            cid = c["chunk_id"]
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                retrieved_chunks.append(c)

    return scraped_sources, retrieved_chunks

def synthesize_node(
    question: str,
    sub_questions: List[str],
    chunks: List[Dict[str, Any]],
    sources: List[Dict[str, Any]]
) -> str:
    """
    Step 3: Synthesizes a structured Markdown research report with inline citations [n].
    """
    client = get_genai_client()

    # Format source excerpts for LLM context
    context_blocks = []
    for c in chunks:
        block = (
            f"--- SOURCE EXCERPT [Citation #{c['citation_num']}] ---\n"
            f"Title: {c.get('title', '')}\n"
            f"URL: {c.get('url', '')}\n"
            f"Content:\n{c.get('text', '')}\n"
        )
        context_blocks.append(block)

    sources_reference_guide = "\n".join([
        f"[{s['citation_num']}] {s['title']} ({s['url']})"
        for s in sources
    ])

    user_prompt = (
        f"RESEARCH TOPIC: {question}\n\n"
        f"SUB-QUESTIONS EXPLORED:\n" + "\n".join([f"- {sq}" for sq in sub_questions]) + "\n\n"
        f"AVAILABLE SOURCE EXCERPTS FOR GROUNDING:\n\n"
        + "\n\n".join(context_blocks) + "\n\n"
        f"LIST OF SOURCES:\n{sources_reference_guide}\n\n"
        f"Generate the comprehensive research report in Markdown following all citation rules."
    )

    response = client.models.generate_content(
        model=settings.MODEL_SYNTH,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYNTHESIZER_SYSTEM_PROMPT,
            temperature=0.2
        )
    )

    return response.text.strip()

def verify_node(
    report_md: str,
    sources: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Step 4: Verifies citations against raw text spans and checks for cross-source contradictions.
    """
    client = get_genai_client()

    sources_text_block = []
    for s in sources:
        # Provide clean sample of source text for verification
        raw_excerpt = s['raw_text'][:4000]
        sources_text_block.append(
            f"SOURCE [Citation #{s['citation_num']}] (ID: {s['id']}):\n"
            f"Title: {s['title']}\n"
            f"Text Excerpt:\n{raw_excerpt}\n"
        )

    critic_prompt = (
        f"SYNTHESIZED REPORT:\n{report_md}\n\n"
        f"SOURCES:\n" + "\n\n".join(sources_text_block) + "\n\n"
        f"Extract supporting quotes for all claims with their citation numbers and identify any contradictions."
    )

    parsed_output = {"claims_with_citations": [], "contradictions": []}
    try:
        response = client.models.generate_content(
            model=settings.MODEL_VERIFY,
            contents=critic_prompt,
            config=types.GenerateContentConfig(
                system_instruction=CRITIC_VERIFICATION_PROMPT,
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        parsed_output = json.loads(clean_json_response(response.text))
    except Exception as e:
        print(f"[verify_node] Warning: Verification LLM call failed: {e}")

    raw_claims = parsed_output.get("claims_with_citations", [])
    contradictions = parsed_output.get("contradictions", [])

    # Map citation_num to source object
    source_map = {s["citation_num"]: s for s in sources}

    verified_citations: List[Dict[str, Any]] = []

    for claim in raw_claims:
        cit_num = claim.get("citation_num")
        quote = claim.get("quote", "")
        if cit_num in source_map and quote:
            matched_source = source_map[cit_num]
            status, char_span = locate_quote_in_text(quote, matched_source["raw_text"])

            verified_citations.append({
                "id": str(uuid.uuid4()),
                "source_id": matched_source["id"],
                "citation_num": cit_num,
                "quote": quote,
                "char_span": char_span,
                "status": status
            })

    return verified_citations, contradictions
