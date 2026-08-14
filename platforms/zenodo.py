import httpx
import logging
from typing import List, Optional, Dict, Any
from .base import PaperSource
from .models import Paper

logger = logging.getLogger(__name__)

class ZenodoSearcher(PaperSource):
    """Search and discover papers on Zenodo via its public REST API."""
    BASE_URL = "https://zenodo.org/api"

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        params = {
            "q": query,
            "size": limit,
            "sort": "mostrecent",
            "type": kwargs.get("type", "publication")
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(f"{self.BASE_URL}/records", params=params)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for hit in data.get("hits", {}).get("hits", []):
                    meta = hit.get("metadata", {})
                    authors = [c.get("name", "") for c in meta.get("creators", [])]
                    
                    papers.append(Paper(
                        paper_id=f"zenodo:{hit.get('id')}",
                        title=meta.get("title", ""),
                        authors=authors,
                        abstract=meta.get("description", ""),
                        doi=hit.get("doi", ""),
                        published_date=meta.get("publication_date", ""),
                        url=hit.get("links", {}).get("html", ""),
                        source="Zenodo"
                    ))
                return papers
            except Exception as e:
                logger.error(f"Zenodo search failed: {e}")
                return []
