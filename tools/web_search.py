import os
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from app.config import settings
from db.session import get_db_session
from db.repositories import get_cache, set_cache, compute_cache_key

class WebSearchTool:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.client = TavilyClient(api_key=self.api_key) if self.api_key else None

    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Executes a web search with SQLite caching.
        Returns a list of dicts: [{'title': ..., 'url': ..., 'snippet': ...}]
        """
        max_results = max_results or settings.MAX_SEARCH_RESULTS_PER_QUERY
        cache_key = compute_cache_key("tavily", f"{query}:{max_results}")

        # 1. Check SQLite Cache
        with get_db_session() as session:
            cached_data = get_cache(session, cache_key)
            if cached_data is not None:
                return cached_data

        # 2. Live Search execution
        results: List[Dict[str, Any]] = []
        if self.client:
            try:
                response = self.client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=max_results,
                    include_answer=False
                )
                for item in response.get("results", []):
                    results.append({
                        "title": item.get("title", "Untitled Source"),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                        "score": item.get("score", 0.0)
                    })
            except Exception as e:
                # Log error and fallback
                print(f"[WebSearchTool] Tavily search error for '{query}': {e}")
        else:
            print(f"[WebSearchTool] Warning: TAVILY_API_KEY not set. Returning empty results for '{query}'.")

        # 3. Store in SQLite Cache if results found
        if results:
            with get_db_session() as session:
                set_cache(session, cache_key, "tavily", results)

        return results

search_tool = WebSearchTool()
