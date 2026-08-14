import random
import asyncio
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class GoogleScholarSearcher(PaperSource):
    """Google Scholar search implementation."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            
            await asyncio.sleep(random.uniform(1.0, 2.5))
            url = f"https://scholar.google.com/scholar?q={query}"
            
            try:
                await page.goto(url, wait_until="networkidle")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                await page.wait_for_selector(".gs_r.gs_or.gs_scl", timeout=15000)
                items = await page.query_selector_all(".gs_r.gs_or.gs_scl")
                for item in items[:limit]:
                    title_el = await item.query_selector(".gs_rt a")
                    if not title_el: title_el = await item.query_selector(".gs_rt")
                    
                    title = await title_el.inner_text() if title_el else "N/A"
                    link = await title_el.get_attribute("href") if title_el else ""
                    
                    meta_el = await item.query_selector(".gs_a")
                    meta = await meta_el.inner_text() if meta_el else ""
                    
                    year_match = re.search(r"\d{4}", meta)
                    author = meta.split("-")[0].strip() if "-" in meta else meta
                    
                    results.append(Paper(
                        paper_id=link if link else title.strip(),
                        title=title.strip(),
                        authors=[author],
                        published_date=year_match.group(0) if year_match else None,
                        url=link,
                        source="GoogleScholar"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results
