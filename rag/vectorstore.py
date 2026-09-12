from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings, BASE_DIR
from rag.embeddings import embeddings_service

# Ensure Chroma storage path exists
chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
chroma_dir.mkdir(parents=True, exist_ok=True)

class ChromaVectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    def _get_collection_name(self, run_id: str) -> str:
        # Chroma collection names must be 3-63 chars, alphanumeric or underscores
        clean_id = run_id.replace("-", "_")
        return f"run_{clean_id}"[:60]

    def index_chunks(self, run_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Embeds and indexes document chunks into a Chroma collection dedicated to this run.
        """
        if not chunks:
            return

        col_name = self._get_collection_name(run_id)
        collection = self.client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"}
        )

        texts = [c["text"] for c in chunks]
        embeddings = embeddings_service.embed_documents(texts)
        ids = [c["chunk_id"] for c in chunks]
        metadatas = [
            {
                "source_id": c["source_id"],
                "citation_num": int(c["citation_num"]),
                "title": c.get("title", ""),
                "url": c.get("url", ""),
                "domain": c.get("domain", ""),
                "start_char": int(c.get("start_char", 0)),
                "end_char": int(c.get("end_char", 0))
            }
            for c in chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    def query_similar_chunks(
        self,
        run_id: str,
        query: str,
        top_k: int = settings.TOP_K_CHUNKS
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most semantically relevant chunks for a given sub-question query.
        """
        col_name = self._get_collection_name(run_id)
        try:
            collection = self.client.get_collection(name=col_name)
        except Exception:
            return []

        query_emb = embeddings_service.embed_query(query)
        total_items = collection.count()
        if total_items == 0:
            return []

        actual_k = min(top_k, total_items)
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"]
        )

        retrieved: List[Dict[str, Any]] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            doc_ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0] if "distances" in results else [0.0] * len(doc_ids)

            for cid, doc, meta, dist in zip(doc_ids, docs, metas, dists):
                retrieved.append({
                    "chunk_id": cid,
                    "text": doc,
                    "source_id": meta.get("source_id", ""),
                    "citation_num": meta.get("citation_num", 1),
                    "title": meta.get("title", ""),
                    "url": meta.get("url", ""),
                    "domain": meta.get("domain", ""),
                    "start_char": meta.get("start_char", 0),
                    "end_char": meta.get("end_char", 0),
                    "similarity_score": round(1.0 - float(dist), 4)  # Cosine similarity
                })

        return retrieved

    def delete_run_collection(self, run_id: str) -> None:
        """Removes the ephemeral collection for a run."""
        col_name = self._get_collection_name(run_id)
        try:
            self.client.delete_collection(name=col_name)
        except Exception:
            pass

vector_store = ChromaVectorStore()
