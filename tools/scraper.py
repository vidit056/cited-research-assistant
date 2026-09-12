import urllib.parse
from typing import Optional, Dict, Any, List
import httpx
import trafilatura
from app.config import settings
from db.session import get_db_session
from db.repositories import get_cache, set_cache, compute_cache_key

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (Research Assistant Bot)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

class WebScraper:
    def __init__(self, timeout_seconds: float = 12.0):
        self.timeout = timeout_seconds

    def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes and extracts clean readable text from a URL with SQLite caching.
        Returns a dictionary with url, domain, title, raw_text, published_date.
        """
        if not url or not url.startswith("http"):
            return None

        cache_key = compute_cache_key("scrape", url)

        # 1. Check SQLite Cache
        with get_db_session() as session:
            cached_data = get_cache(session, cache_key)
            if cached_data is not None:
                return cached_data

        domain = urllib.parse.urlparse(url).netloc

        # 2. Live HTTP fetch & Trafilatura text extraction
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
                response = client.get(url)
                if response.status_code >= 400:
                    return None
                html_content = response.text

            # Extract main readable text
            extracted_text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )

            if not extracted_text or len(extracted_text.strip()) < 50:
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(html_content)
            title = (metadata.title if metadata and metadata.title else domain)
            published_date = (metadata.date if metadata and metadata.date else None)

            result = {
                "url": url,
                "domain": domain,
                "title": title,
                "published_date": published_date,
                "raw_text": extracted_text.strip()
            }

            # 3. Store in SQLite Cache
            with get_db_session() as session:
                set_cache(session, cache_key, "scrape", result)

            return result

        except Exception as e:
            print(f"[WebScraper] Failed to scrape {url}: {e}")
            return None

    def scrape_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrapes multiple URLs sequentially or from cache."""
        results = []
        for u in urls:
            res = self.scrape(u)
            if res:
                results.append(res)
        return results

scraper_tool = WebScraper()
