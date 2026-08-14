from typing import List
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class BOESearcher(PaperSource):
    """BOE - Boletín Oficial del Estado (Spanish legislation)."""

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://www.boe.es/buscar/legislacion.php?campo%5B2%5D=TITULOS&dato%5B2%5D={query.replace(' ', '+')}&accion=Buscar&sort_field%5B0%5D=PESO&sort_order%5B0%5D=desc"
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                items = await page.evaluate('''(limit) => {
                    const results = document.querySelectorAll('.resultado-busqueda');
                    return Array.from(results).slice(0, limit).map(el => {
                        const text = el.innerText;
                        const a = el.querySelector('a');
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 5);
                        const title = lines.length > 1 ? lines[1] : (lines[0] || 'N/A');
                        const link = a ? a.href : '';
                        const yearMatch = text.match(/\\b(19|20)\\d{2}\\b/);
                        const refMatch = text.match(/BOE-[A-Z]-\\d{4}-\\d+/);
                        return {
                            title: title.substring(0, 300),
                            url: link,
                            year: yearMatch ? yearMatch[0] : '',
                            ref: refMatch ? refMatch[0] : ''
                        };
                    });
                }''', limit)
                
                for item in items:
                    results.append(Paper(
                        paper_id=item["ref"] or item["url"].split('=')[-1],
                        title=item["title"],
                        authors=["Gobierno de España"],
                        published_date=item["year"],
                        url=item["url"],
                        source="BOE"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results
