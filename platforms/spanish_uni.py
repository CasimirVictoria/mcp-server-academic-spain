from typing import List
import urllib.parse
from playwright.async_api import async_playwright
from .base import PaperSource
from .models import Paper
from .core import StealthBrowser, FirecrawlClient

class TeseoSearcher(PaperSource):
    """TESEO - Spanish Doctoral Theses."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            try:
                await page.goto("https://aplicaciones.ciencia.gob.es/teseo/")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url("https://aplicaciones.ciencia.gob.es/teseo/")
                
                await page.wait_for_selector("#contenido", timeout=15000)
                await page.fill("#contenido", query)
                await page.click(".buttonForm")
                
                await page.wait_for_selector("mat-row", timeout=20000)
                
                items = await page.evaluate(f'''() => {{
                    const rows = Array.from(document.querySelectorAll('mat-row'));
                    return rows.map(row => {{
                        const titleEl = row.querySelector('.cdk-column-titulo span');
                        const authorEl = row.querySelector('.cdk-column-autor span');
                        return {{
                            title: titleEl ? titleEl.innerText.trim() : 'Sense títol',
                            author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                        }};
                    }});
                }}''')
                
                for item in items[:limit]:
                    results.append(Paper(
                        paper_id=item["title"],
                        title=item["title"],
                        authors=[item["author"]],
                        url="https://aplicaciones.ciencia.gob.es/teseo/",
                        source="TESEO"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results

class GVASearcher(PaperSource):
    """Generalitat Valenciana (DOGV/Portal Legislativo) - Education Laws."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = "https://dogv.gva.es/es/cerca-de-legislacio"
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    await firecrawl.scrape_url(url)
                
                await page.wait_for_selector(".search-input", timeout=15000)
                checkbox = await page.query_selector("input[type='checkbox']")
                if checkbox and await checkbox.is_checked():
                    await checkbox.uncheck()
                
                await page.fill(".search-input", query)
                await page.keyboard.press("Enter")
                
                try:
                    await page.wait_for_selector("a.cursor-unset, .card", timeout=15000)
                except:
                    await page.wait_for_load_state("networkidle")
                
                items = await page.evaluate(f'''() => {{
                    const items = Array.from(document.querySelectorAll('a.cursor-unset, .card'));
                    return items.map(item => {{
                        const titleEl = item.querySelector('p');
                        const deptEl = item.querySelector('h5');
                        const sigMatch = item.innerText.match(/\\d{{4}}\\/\\d+/);
                        const signature = sigMatch ? sigMatch[0] : null;
                        
                        return {{
                            title: titleEl ? titleEl.innerText.trim() : 'Normativa GVA',
                            url: signature ? `https://dogv.gva.es/es/disposicio?sig=${{signature}}` : 'https://dogv.gva.es/es/cerca-de-legislacio',
                            author: deptEl ? deptEl.innerText.trim() : 'Generalitat Valenciana',
                        }};
                    }}).filter(res => res.title.length > 10);
                }}''')
                
                for item in items[:limit]:
                    results.append(Paper(
                        paper_id=item["url"].split('=')[-1] if '=' in item["url"] else item["title"],
                        title=item["title"],
                        authors=[item["author"]],
                        url=item["url"],
                        source="GVA (DOGV)"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results

class RodericSearcher(PaperSource):
    """RODERIC - Universitat de València Institutional Repository."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://roderic.uv.es/search?query={query.replace(' ', '+')}"
            try:
                await page.goto(url, wait_until="networkidle")
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    raise Exception("Blocked by university WAF/Firewall (common on cloud/datacenter IPs, but works on local residential connections)")
                
                await page.wait_for_selector("ds-item-search-result-list-element", timeout=20000)
                
                items = await page.evaluate(f'''() => {{
                    const items = Array.from(document.querySelectorAll('ds-item-search-result-list-element'));
                    return items.map(item => {{
                        const titleEl = item.querySelector('a.item-list-title');
                        const authorEl = item.querySelector('.item-list-authors');
                        const dateEl = item.querySelector('.item-list-date');
                        const abstractEl = item.querySelector('.item-list-abstract');
                        
                        return {{
                            title: titleEl ? titleEl.innerText.trim() : 'N/A',
                            url: titleEl ? titleEl.href : 'https://roderic.uv.es/',
                            author: authorEl ? authorEl.innerText.trim() : 'Universitat de València',
                            year: dateEl ? dateEl.innerText.trim().replace(/[()]/g, '') : 'N/A',
                            abstract: abstractEl ? abstractEl.innerText.trim() : ''
                        }};
                    }});
                }}''')
                
                for item in items[:limit]:
                    results.append(Paper(
                        paper_id=item["url"].split('/')[-1],
                        title=item["title"],
                        authors=[item["author"]],
                        published_date=item["year"],
                        abstract=item["abstract"],
                        url=item["url"],
                        source="RODERIC (UV)"
                    ))
            except Exception:
                pass
            finally:
                await browser.close()
        return results

class TDRSearcher(PaperSource):
    """TDR - Tesis Doctorals en Xarxa (Catalan/Spanish doctoral theses)."""
    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://www.tdx.cat/discover?query={urllib.parse.quote(query)}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    firecrawl = FirecrawlClient()
                    if firecrawl.api_key:
                        # Fallback to Firecrawl if blocked
                        pass
                
                await page.wait_for_selector(".ds-artifact-item", timeout=12000)
                items = await page.query_selector_all(".ds-artifact-item")
                for item in items[:limit]:
                    title_el = await item.query_selector(".artifact-title a")
                    title = await title_el.inner_text() if title_el else "N/A"
                    link = await title_el.get_attribute("href") if title_el else "N/A"
                    author_el = await item.query_selector(".author")
                    author = await author_el.inner_text() if author_el else "Autor desconegut"
                    date_el = await item.query_selector(".publisher-date")
                    date_text = await date_el.inner_text() if date_el else ""
                    year = None
                    if date_text:
                        import re
                        match = re.search(r"\b(19|20)\d{2}\b", date_text)
                        if match: year = int(match.group(0))

                    results.append(Paper(
                        title=title.strip(),
                        url=f"https://www.tdx.cat{link}" if link.startswith("/") else link,
                        authors=[author.strip()],
                        year=year,
                        source="TDR (TDX)"
                    ))
            except Exception as e:
                import logging
                logging.error(f"TDR search error: {e}")
            finally:
                await browser.close()
        return results

class RiunetSearcher(PaperSource):
    """RIUNET - Universitat Politècnica de València Institutional Repository."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://riunet.upv.es/discover?query={urllib.parse.quote(query)}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    raise Exception("Blocked by university WAF/Firewall (common on cloud/datacenter IPs, but works on local residential connections)")
                
                await page.wait_for_selector("ds-item-search-result-list-element, .ds-artifact-item, h4.artifact-title", timeout=20000)
                
                items = await page.evaluate('''() => {
                    let ds7Items = Array.from(document.querySelectorAll('ds-item-search-result-list-element'));
                    if (ds7Items.length > 0) {
                        return ds7Items.map(item => {
                            const titleEl = item.querySelector('a.item-list-title, a[href*="/handle/"]');
                            const authorEl = item.querySelector('.item-list-authors, .item-list-author');
                            const dateEl = item.querySelector('.item-list-date, .item-list-year');
                            const abstractEl = item.querySelector('.item-list-abstract, .item-list-description');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    
                    let ds5Items = Array.from(document.querySelectorAll('.ds-artifact-item, .artifact-description'));
                    if (ds5Items.length > 0) {
                        return ds5Items.map(item => {
                            const titleEl = item.querySelector('.artifact-title a, h4.artifact-title a');
                            const authorEl = item.querySelector('.author, .artifact-author');
                            const dateEl = item.querySelector('.publisher-date, .date, .artifact-date');
                            const abstractEl = item.querySelector('.abstract, .artifact-abstract');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    return [];
                }''')
                
                for item in items[:limit]:
                    title = item["title"]
                    link = item["url"]
                    author = item["author"]
                    date_text = item["year"]
                    
                    year = None
                    if date_text:
                        import re
                        match = re.search(r"\b(19|20)\d{2}\b", date_text)
                        if match: year = int(match.group(0))

                    results.append(Paper(
                        paper_id=link.split('/')[-1] if link else "",
                        title=title,
                        url=link,
                        authors=[author.rstrip(';')],
                        published_date=str(year) if year else None,
                        abstract=item.get("abstract", ""),
                        source="RIUNET (UPV)"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"RIUNET search error: {e}")
            finally:
                await browser.close()
        return results

class RuaSearcher(PaperSource):
    """RUA - Universitat d'Alacant Institutional Repository."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://rua.ua.es/discover?query={urllib.parse.quote(query)}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    raise Exception("Blocked by university WAF/Firewall (common on cloud/datacenter IPs, but works on local residential connections)")
                
                await page.wait_for_selector("ds-item-search-result-list-element, .ds-artifact-item, h4.artifact-title", timeout=20000)
                
                items = await page.evaluate('''() => {
                    let ds7Items = Array.from(document.querySelectorAll('ds-item-search-result-list-element'));
                    if (ds7Items.length > 0) {
                        return ds7Items.map(item => {
                            const titleEl = item.querySelector('a.item-list-title, a[href*="/handle/"]');
                            const authorEl = item.querySelector('.item-list-authors, .item-list-author');
                            const dateEl = item.querySelector('.item-list-date, .item-list-year');
                            const abstractEl = item.querySelector('.item-list-abstract, .item-list-description');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    
                    let ds5Items = Array.from(document.querySelectorAll('.ds-artifact-item, .artifact-description'));
                    if (ds5Items.length > 0) {
                        return ds5Items.map(item => {
                            const titleEl = item.querySelector('.artifact-title a, h4.artifact-title a');
                            const authorEl = item.querySelector('.author, .artifact-author');
                            const dateEl = item.querySelector('.publisher-date, .date, .artifact-date');
                            const abstractEl = item.querySelector('.abstract, .artifact-abstract');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    return [];
                }''')
                
                for item in items[:limit]:
                    title = item["title"]
                    link = item["url"]
                    author = item["author"]
                    date_text = item["year"]
                    
                    year = None
                    if date_text:
                        import re
                        match = re.search(r"\b(19|20)\d{2}\b", date_text)
                        if match: year = int(match.group(0))

                    results.append(Paper(
                        paper_id=link.split('/')[-1] if link else "",
                        title=title,
                        url=link,
                        authors=[author.rstrip(';')],
                        published_date=str(year) if year else None,
                        abstract=item.get("abstract", ""),
                        source="RUA (UA)"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"RUA search error: {e}")
            finally:
                await browser.close()
        return results

class UjiSearcher(PaperSource):
    """uji.repositori - Universitat Jaume I Institutional Repository."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = f"https://repositori.uji.es/discover?query={urllib.parse.quote(query)}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await StealthBrowser.human_scroll(page)
                
                if await StealthBrowser.is_blocked(page):
                    raise Exception("Blocked by university WAF/Firewall (common on cloud/datacenter IPs, but works on local residential connections)")
                
                await page.wait_for_selector("ds-item-search-result-list-element, .ds-artifact-item, h4.artifact-title", timeout=20000)
                
                items = await page.evaluate('''() => {
                    let ds7Items = Array.from(document.querySelectorAll('ds-item-search-result-list-element'));
                    if (ds7Items.length > 0) {
                        return ds7Items.map(item => {
                            const titleEl = item.querySelector('a.item-list-title, a[href*="/handle/"]');
                            const authorEl = item.querySelector('.item-list-authors, .item-list-author');
                            const dateEl = item.querySelector('.item-list-date, .item-list-year');
                            const abstractEl = item.querySelector('.item-list-abstract, .item-list-description');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    
                    let ds5Items = Array.from(document.querySelectorAll('.ds-artifact-item, .artifact-description'));
                    if (ds5Items.length > 0) {
                        return ds5Items.map(item => {
                            const titleEl = item.querySelector('.artifact-title a, h4.artifact-title a');
                            const authorEl = item.querySelector('.author, .artifact-author');
                            const dateEl = item.querySelector('.publisher-date, .date, .artifact-date');
                            const abstractEl = item.querySelector('.abstract, .artifact-abstract');
                            return {
                                title: titleEl ? titleEl.innerText.trim() : 'N/A',
                                url: titleEl ? titleEl.href : '',
                                author: authorEl ? authorEl.innerText.trim() : 'Autor desconegut',
                                year: dateEl ? dateEl.innerText.trim() : 'N/A',
                                abstract: abstractEl ? abstractEl.innerText.trim() : ''
                            };
                        });
                    }
                    return [];
                }''')
                
                for item in items[:limit]:
                    title = item["title"]
                    link = item["url"]
                    author = item["author"]
                    date_text = item["year"]
                    
                    year = None
                    if date_text:
                        import re
                        match = re.search(r"\b(19|20)\d{2}\b", date_text)
                        if match: year = int(match.group(0))

                    results.append(Paper(
                        paper_id=link.split('/')[-1] if link else "",
                        title=title,
                        url=link,
                        authors=[author.rstrip(';')],
                        published_date=str(year) if year else None,
                        abstract=item.get("abstract", ""),
                        source="UJI Repositori"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"UJI repositori search error: {e}")
            finally:
                await browser.close()
        return results

class RebiunSearcher(PaperSource):
    """REBIUN - Red de Bibliotecas Universitarias Españolas Collective Catalog."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await StealthBrowser.get_context(browser)
            page = await context.new_page()
            url = "https://rebiun.baratz.es/OpacDiscovery/"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Type the query and submit
                await page.type("input#mainAccessLink", query)
                await page.keyboard.press("Enter")
                
                # Wait for search results
                await page.wait_for_selector(".cont_item_titles", timeout=15000)
                
                items = await page.query_selector_all(".cont_item_titles")
                for item in items[:limit]:
                    title_el = await item.query_selector("h3.item-title a")
                    title = await title_el.inner_text() if title_el else "Sense títol"
                    link = await title_el.get_attribute("href") if title_el else ""
                    
                    author_el = await item.query_selector(".item-authority")
                    author = await author_el.inner_text() if author_el else ""
                    author = author.strip() if author else "Desconegut"
                    
                    pub_el = await item.query_selector(".item-publication")
                    pub_text = await pub_el.inner_text() if pub_el else ""
                    
                    year = None
                    if pub_text:
                        import re
                        match = re.search(r"\b(19|20)\d{2}\b", pub_text)
                        if match: year = int(match.group(0))
                        
                    results.append(Paper(
                        paper_id=link.split('/')[-1].split('?')[0] if link else "",
                        title=title.strip(),
                        authors=[author] if author else [],
                        published_date=str(year) if year else None,
                        url=f"https://rebiun.baratz.es{link}" if link.startswith("/") else link,
                        source="REBIUN"
                    ))
            except Exception as e:
                import logging
                logging.getLogger("academic-spain-mcp").error(f"REBIUN search error: {e}")
            finally:
                await browser.close()
        return results
