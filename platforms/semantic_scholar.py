import httpx
import asyncio
import os
from typing import List, Dict, Any, Optional
from .base import PaperSource
from .models import Paper

class SemanticScholarSearcher(PaperSource):
    """Semantic Scholar API search implementation."""
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    _last_request_time = 0.0
    _lock = asyncio.Lock()

    def __init__(self):
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    async def _rate_limit(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < 1.1:
                await asyncio.sleep(1.1 - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        await self._rate_limit()
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "query": query,
                "limit": limit,
                "fields": "title,url,authors,year,citationCount,abstract,externalIds,journal,publicationVenue"
            }
            for attempt in range(3):
                try:
                    response = await client.get(f"{self.BASE_URL}/paper/search", params=params, headers=headers)
                    if response.status_code == 429:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    if not response.is_success:
                        return []
                    
                    data = response.json().get("data", []) or []
                    papers = []
                    for item in data:
                        authors = [a.get("name", "") for a in item.get("authors", [])]
                        ext_ids = item.get("externalIds") or {}
                        doi = ext_ids.get("DOI", "")
                        journal = (item.get("journal") or {}).get("name") or (item.get("publicationVenue") or {}).get("name", "")
                        
                        papers.append(Paper(
                            paper_id=item.get("paperId") or "",
                            title=item.get("title") or "N/A",
                            authors=authors,
                            abstract=item.get("abstract") or "",
                            doi=doi,
                            published_date=str(item.get("year")) if item.get("year") else None,
                            url=item.get("url") or "",
                            source="Semantic Scholar",
                            citations=item.get("citationCount", 0),
                            extra={"journal": journal}
                        ))
                    return papers
                except Exception:
                    await asyncio.sleep(1)
        return []
