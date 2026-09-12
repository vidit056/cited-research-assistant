from typing import List, Dict, Any
from app.config import settings

def chunk_text(
    text: str,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping chunks respecting sentence/paragraph boundaries.
    Returns list of dicts with text and character start/end offsets.
    """
    if not text:
        return []

    chunks: List[Dict[str, Any]] = []
    text_len = len(text)
    start = 0

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # If not at the very end of the text, try to find a natural break point (paragraph or sentence)
        if end < text_len:
            # Look backwards from end for paragraph break '\n\n'
            break_pos = text.rfind("\n\n", start + chunk_size // 2, end)
            if break_pos == -1:
                # Look for sentence boundary '. '
                break_pos = text.rfind(". ", start + chunk_size // 2, end)
                if break_pos != -1:
                    break_pos += 1  # Include the period
            if break_pos == -1:
                # Look for space
                break_pos = text.rfind(" ", start + chunk_size // 2, end)

            if break_pos != -1 and break_pos > start:
                end = break_pos

        chunk_str = text[start:end].strip()
        if chunk_str:
            chunks.append({
                "text": chunk_str,
                "start_char": start,
                "end_char": end
            })

        # Advance start position by step size (chunk_size - overlap)
        step = max(1, (end - start) - chunk_overlap) if end < text_len else (end - start)
        start += step

    return chunks

def ingest_source_to_chunks(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Converts a single source record into indexed chunks with full provenance metadata.
    """
    raw_text = source.get("raw_text", "")
    source_id = source.get("id", "")
    citation_num = source.get("citation_num", 1)
    title = source.get("title", "")
    url = source.get("url", "")
    domain = source.get("domain", "")

    raw_chunks = chunk_text(raw_text)
    enriched_chunks: List[Dict[str, Any]] = []

    for i, c in enumerate(raw_chunks):
        enriched_chunks.append({
            "chunk_id": f"{source_id}_c{i}",
            "source_id": source_id,
            "citation_num": citation_num,
            "title": title,
            "url": url,
            "domain": domain,
            "text": c["text"],
            "start_char": c["start_char"],
            "end_char": c["end_char"]
        })

    return enriched_chunks
