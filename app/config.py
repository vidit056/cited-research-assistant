import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from google import genai

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Google Cloud Vertex AI
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "project-537fe30e-f4c9-4e18-8c3")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "global")

    # Search Tool (Tavily)
    TAVILY_API_KEY: str = ""

    # Database & Storage
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / '.data' / 'app.db'}"
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / ".data" / "chroma")

    # Per-step LLM model knobs (all defaulting to gemini-3.7-flash for v1 MVP)
    MODEL_PLAN: str = "gemini-3.7-flash"
    MODEL_RETRIEVE: str = "gemini-3.7-flash"
    MODEL_SYNTH: str = "gemini-3.7-flash"
    MODEL_VERIFY: str = "gemini-3.7-flash"

    # Embedding model
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Citation Fuzzy Match Threshold (rapidfuzz partial_ratio)
    CITATION_MATCH_THRESHOLD: float = 85.0

    # Search & Scraping limits
    MAX_SEARCH_RESULTS_PER_QUERY: int = 5
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    TOP_K_CHUNKS: int = 4

settings = Settings()

def get_genai_client() -> genai.Client:
    """Returns a unified Google GenAI client configured for Vertex AI mode."""
    return genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.VERTEX_LOCATION,
    )
