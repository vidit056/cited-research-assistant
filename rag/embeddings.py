from typing import List
from app.config import get_genai_client, settings

class VertexEmbeddings:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self.client = get_genai_client()

    def embed_query(self, text: str) -> List[float]:
        """Generates embedding for a single query string."""
        clean_text = text.strip() or "empty query"
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=clean_text
        )
        return list(response.embeddings[0].values)

    def embed_documents(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """Generates embeddings for a list of document strings in batches."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = [t.strip() or "empty chunk" for t in texts[i:i + batch_size]]
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=batch
            )
            for emb in response.embeddings:
                all_embeddings.append(list(emb.values))

        return all_embeddings

embeddings_service = VertexEmbeddings()
