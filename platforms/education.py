from typing import List
import httpx
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser

class EricSearcher(PaperSource):
    """ERIC - Education Resources Information Center."""
    BASE_URL = "https://api.ies.ed.gov/eric"

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "search": query,
                "rows": limit,
                "format": "json",
                "fields": "id,title,author,source,publicationdateyear,issn,description,peerreviewed"
            }
            try:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                results = data.get("response", {}).get("docs", [])
                output = []
                for item in results:
                    authors_raw = item.get("author", [])
                    authors_list = authors_raw if isinstance(authors_raw, list) else ([authors_raw] if authors_raw else [])
                    
                    output.append(Paper(
                        paper_id=item.get("id", ""),
                        title=item.get("title", "Sense títol"),
                        authors=authors_list,
                        published_date=str(item.get("publicationdateyear") or item.get("pubyear", "")),
                        url=f"https://eric.ed.gov/?id={item.get('id')}" if item.get('id') else "https://eric.ed.gov/",
                        journal=item.get("source", ""),
                        abstract=item.get("description", ""),
                        source="ERIC"
                    ))
                return output
            except Exception:
                return []

class EurekaSearcher(PaperSource):
    """Revista Eureka sobre Enseñanza y Divulgación de las Ciencias."""
    BASE_URL = "https://revistas.uca.es/index.php/eureka/search/index"
    
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.BASE_URL, params={"query": query})
                if response.status_code != 200: return []
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select(".obj_article_summary")
                output = []
                for item in items[:limit]:
                    title_el = item.select_one(".title a")
                    author_el = item.select_one(".authors")
                    date_el = item.select_one(".published")
                    
                    year = "N/A"
                    if date_el:
                        year_match = re.search(r"\d{4}", date_el.get_text())
                        if year_match:
                            year = year_match[0]
                            
                    output.append(Paper(
                        paper_id=title_el["href"].split("/")[-1] if title_el else "eureka-" + str(len(output)),
                        title=title_el.get_text(strip=True) if title_el else "N/A",
                        authors=[author_el.get_text(strip=True)] if author_el else [],
                        published_date=year,
                        url=title_el["href"] if title_el else "https://revistas.uca.es/index.php/eureka/",
                        source="RevistaEureka"
                    ))
                return output
            except Exception:
                return []

class IntefSearcher(PaperSource):
    """INTEF - Instituto Nacional de Tecnologías Educativas y de Formación del Profesorado."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        import urllib.parse
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://intef.es/?s={urllib.parse.quote(query)}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await StealthBrowser.human_scroll(page)
                
                await page.wait_for_selector(".post-title a", timeout=12000)
                items = await page.query_selector_all(".post-title a")
                for item in items[:limit]:
                    title = await item.inner_text()
                    link = await item.get_attribute("href")
                    
                    results.append(Paper(
                        paper_id=link.split('/')[-2] if link else "intef-" + str(len(results)),
                        title=title.strip(),
                        authors=["INTEF"],
                        url=link or "",
                        source="INTEF"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"INTEF search error: {e}")
            finally:
                await browser.close()
        return results
