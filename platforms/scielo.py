from typing import List
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class ScieloSearcher(PaperSource):
    """SciELO - Scientific Electronic Library Online."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://search.scielo.org/?q={query.replace(' ', '+')}&lang=es"
            
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                await page.wait_for_selector(".line", timeout=15000)
                
                items = await page.evaluate(f'''() => {{
                    const rows = Array.from(document.querySelectorAll('.line'));
                    return rows.map(row => {{
                        const titleEl = row.querySelector('a strong');
                        const linkEl = row.querySelector('a[href*="script=sci_arttext"]');
                        return {{
                            title: titleEl ? titleEl.innerText.trim() : 'Sense títol',
                            url: linkEl ? linkEl.href : '',
                        }};
                    }}).filter(res => res.url !== "");
                }}''')
                
                for item in items[:limit]:
                    results.append(Paper(
                        paper_id=item["url"].split('pid=')[-1].split('&')[0] if 'pid=' in item["url"] else item["url"],
                        title=item["title"],
                        authors=["SciELO Author"],
                        url=item["url"],
                        source="SciELO"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results
