import httpx
from typing import List, Dict, Any, Optional
from .base import PaperSource
from .models import Paper

def reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    if not inverted_index:
        return ""
    positions = []
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions.append((idx, word))
    positions.sort()
    return " ".join([word for _, word in positions])

class OpenAlexSearcher(PaperSource):
    """OpenAlex API search implementation."""
    BASE_URL = "https://api.openalex.org"

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"search": query, "per_page": limit, "sort": "cited_by_count:desc"}
            if "filters" in kwargs:
                filter_str = ",".join([f"{k}:{v}" for k, v in kwargs["filters"].items()])
                params["filter"] = filter_str
            
            response = await client.get(f"{self.BASE_URL}/works", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
            
            papers = []
            for res in results:
                authors = [a.get("author", {}).get("display_name", "") for a in res.get("authorships", [])]
                raw_abstract = res.get("abstract_inverted_index", None)
                abstract_text = reconstruct_abstract(raw_abstract)
                
                # DOI handling
                doi = res.get("doi", "") or ""
                # ensure DOI starts with https://doi.org/
                if doi and not doi.startswith("http"):
                    doi = f"https://doi.org/{doi}"

                papers.append(Paper(
                    paper_id=res.get("id", "").replace("https://openalex.org/", ""),
                    title=res.get("display_name", "") or "Sense títol",
                    authors=authors,
                    abstract=abstract_text,
                    doi=doi,
                    published_date=res.get("publication_date", ""),
                    url=res.get("id", ""),
                    pdf_url=res.get("open_access", {}).get("oa_url", "") or "",
                    source="OpenAlex",
                    citations=res.get("cited_by_count", 0)
                ))
            return papers

    async def get_work(self, work_id: str) -> Optional[Paper]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if work_id.startswith("https://openalex.org/"):
                oa_id = work_id.replace("https://openalex.org/", "")
                url = f"{self.BASE_URL}/works/{oa_id}"
            elif work_id.startswith("https://doi.org/"):
                url = f"{self.BASE_URL}/works/{work_id}"
            elif work_id.startswith("http"):
                url = work_id
            elif work_id.startswith("W") and work_id[1:].isdigit():
                url = f"{self.BASE_URL}/works/{work_id}"
            elif "/" in work_id:
                url = f"{self.BASE_URL}/works/https://doi.org/{work_id}"
            else:
                url = f"{self.BASE_URL}/works/{work_id}"
            
            response = await client.get(url)
            if response.status_code != 200:
                return None
            res = response.json()
            
            authors = [a.get("author", {}).get("display_name", "") for a in res.get("authorships", [])]
            raw_abstract = res.get("abstract_inverted_index", None)
            abstract_text = reconstruct_abstract(raw_abstract)
            
            doi = res.get("doi", "") or ""
            if doi and not doi.startswith("http"):
                doi = f"https://doi.org/{doi}"

            return Paper(
                paper_id=res.get("id", "").replace("https://openalex.org/", ""),
                title=res.get("display_name", "") or "Sense títol",
                authors=authors,
                abstract=abstract_text,
                doi=doi,
                published_date=res.get("publication_date", ""),
                url=res.get("id", ""),
                pdf_url=res.get("open_access", {}).get("oa_url", "") or "",
                source="OpenAlex",
                citations=res.get("cited_by_count", 0)
            )
