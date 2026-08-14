from typing import List
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class RedinedSearcher(PaperSource):
    """Redined search implementation (Spanish educational repository)."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://redined.educacion.gob.es/xmlui/discover?query={query}"
            try:
                await page.goto(url, wait_until="networkidle")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                await page.wait_for_selector(".ds-artifact-item", timeout=10000)
                items = await page.query_selector_all(".ds-artifact-item")
                for item in items[:limit]:
                    title_el = await item.query_selector('h4.artifact-title a')
                    title = await title_el.inner_text() if title_el else "N/A"
                    link = await title_el.get_attribute('href') if title_el else "N/A"
                    author_el = await item.query_selector('.author')
                    author = await author_el.inner_text() if author_el else "N/A"
                    date_el = await item.query_selector('.date')
                    date = await date_el.inner_text() if date_el else ""
                    
                    results.append(Paper(
                        paper_id=link.split('/')[-1] if link != "N/A" else "",
                        title=title.strip(),
                        authors=[author.strip().rstrip(';')],
                        published_date=date.strip().lstrip('.').strip(),
                        url=f"https://redined.educacion.gob.es{link}" if link != "N/A" else "",
                        source="Redined"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results
