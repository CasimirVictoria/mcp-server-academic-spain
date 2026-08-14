import urllib.parse
import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class DialnetSearcher(PaperSource):
    """Dialnet search implementation (Spanish/Catalan academic repository)."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        encoded_query = urllib.parse.quote(query)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://dialnet.unirioja.es/buscar/documentos?querysDismax.DOCUMENTAL_TODO={encoded_query}"
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await StealthBrowser.wait_for_cloudflare_challenge(page)
                await asyncio.sleep(2)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                body_text = await page.locator("body").inner_text()
                if "no devuelve ningún resultado" in body_text or "No se han encontrado documentos" in body_text:
                    return []
                
                await page.wait_for_selector(".articulo, .tesis", timeout=20000)
                docs = await page.query_selector_all(".articulo, .tesis")
                for doc in docs[:limit]:
                    title_elem = await doc.query_selector(".titulo a")
                    title = await title_elem.inner_text() if title_elem else "Sense títol"
                    link = await title_elem.get_attribute("href") if title_elem else ""
                    author_elem = await doc.query_selector(".autores")
                    author_name = await author_elem.inner_text() if author_elem else "Desconegut"
                    
                    results.append(Paper(
                        paper_id=link.split('/')[-1] if link else "",
                        title=title.strip(),
                        authors=[author_name.strip()],
                        url=f"https://dialnet.unirioja.es{link}" if link else "",
                        source="Dialnet"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"Dialnet search error: {e}")
            finally:
                await browser.close()
        return results
