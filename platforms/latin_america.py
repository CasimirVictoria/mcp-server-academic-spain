import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base import PaperSource
from .models import Paper

class RedalycSearcher(PaperSource):
    """Redalyc - Scientific Information System (Latin America, Spain, Portugal)."""
    BASE_URL = "https://www.redalyc.org/busquedaArticuloFiltros.oa"
    
    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.BASE_URL, params={"q": query})
                if response.status_code != 200: return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select(".articulo-busqueda") # Potential selector
                if not items: return []
                
                output = []
                for item in items[:limit]:
                    title_el = item.select_one(".titulo")
                    link_el = item.select_one("a")
                    output.append(Paper(
                        title=title_el.get_text(strip=True) if title_el else "N/A",
                        url=link_el["href"] if link_el else "N/A",
                        authors=[],
                        source="Redalyc"
                    ))
                return output
            except Exception: return []
