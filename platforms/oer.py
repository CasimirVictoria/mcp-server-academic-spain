from typing import List
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class ProcomunSearcher(PaperSource):
    """INTEF/Procomún - Open Educational Resources."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://procomun.intef.es/search-full/{query.replace(' ', '%20')}"
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                await page.wait_for_selector(".view-content", timeout=15000)
                
                items = await page.evaluate(f'''() => {{
                    const items = Array.from(document.querySelectorAll('a[href^="/view-resource/"]'));
                    return items.map(item => ({{
                        title: item.innerText.trim(),
                        url: item.href,
                    }})).filter(res => res.title.length > 5);
                }}''')
                
                for item in items[:limit]:
                    results.append(Paper(
                        paper_id=item["url"].split('/')[-1],
                        title=item["title"],
                        authors=["INTEF / Procomún"],
                        url=item["url"],
                        source="Procomun"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results
