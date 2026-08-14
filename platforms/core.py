import os
import re
import json
import asyncio
import random
import tempfile
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class QueryExpander:
    """Expands educational queries with Spanish/Catalan specific terminology."""
    
    EXPANSIONS = {
        "pensament computacional": ["pensamiento computacional", "programación por bloques", "robótica educativa", "competencia digital", "computational thinking"],
        "pensamiento computacional": ["pensament computacional", "programación por bloques", "robótica educativa", "competencia digital", "computational thinking"],
        "aprenentatge basat en projectes": ["ABP", "aprendizaje basado en proyectos", "project-based learning", "metodologías activas"],
        "aprendizaje basado en proyectos": ["ABP", "aprenentatge basat en projectes", "project-based learning", "metodologías activas"],
        "educació inclusiva": ["necesidades educativas especiales", "NEE", "DUA", "diseño universal para el aprendizaje", "inclusión educativa"],
        "educación inclusiva": ["educació inclusiva", "necesidades educativas especiales", "NEE", "DUA", "diseño universal para el aprendizaje", "inclusión educativa"],
        "avaluació": ["evaluación formativa", "rúbricas de evaluación", "criterios de evaluación", "LOMLOE", "competencias clave"],
        "evaluación": ["avaluació", "evaluación formativa", "rúbricas de evaluación", "criterios de evaluación", "LOMLOE", "competencias clave"],
        "gamificació": ["gamificación educativa", "ABJ", "aprendizaje basado en juegos", "game-based learning"],
        "gamificación": ["gamificació", "gamificación educativa", "ABJ", "aprendizaje basado en juegos", "game-based learning"],
        "intel·ligència artificial": ["IA en educación", "inteligencia artificial generativa", "ética IA", "alfabetización digital"],
        "inteligencia artificial": ["intel·ligència artificial", "IA en educación", "inteligencia artificial generativa", "ética IA", "alfabetización digital"],
        "física i química": ["didáctica de la física", "laboratorio virtual", "enseñanza de las ciencias", "STEM"],
        "física y química": ["física i química", "didáctica de la física", "laboratorio virtual", "enseñanza de las ciencias", "STEM"],
        "dual": ["formación profesional dual", "FP dual", "aprendizaje en alternancia"],
        "lomloe": ["situaciones de aprendizaje", "perfil de salida", "saberes básicos", "competencias específicas"],
        "gva": ["Generalitat Valenciana", "DOGV", "Conselleria d'Educació", "normativa educativa valenciana", "Portal Legislativo"],
        "valencia": ["Generalitat Valenciana", "DOGV", "Conselleria d'Educació", "normativa educativa valenciana", "currículum secundària València"]
    }

    def expand(self, query: str) -> List[str]:
        query_lower = query.lower().strip()
        suggestions = []
        for key, terms in self.EXPANSIONS.items():
            if key in query_lower or query_lower in key:
                suggestions.extend(terms)
        if len(suggestions) < 3:
            suggestions.append(f"{query} primaria")
            suggestions.append(f"{query} secundaria")
            suggestions.append(f"{query} universitat")
        return list(dict.fromkeys(suggestions))[:8]

class StealthBrowser:
    """Helper to configure Playwright with stealth settings and detect blocks."""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]
    WEBGL_CONFIGS = [
        {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Intel Inc.", "renderer": "Intel(R) Iris(TM) Plus Graphics 640"},
        {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Apple Inc.", "renderer": "Apple M1"},
        {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"}
    ]

    @staticmethod
    async def get_context(browser):
        ua = random.choice(StealthBrowser.USER_AGENTS)
        webgl = random.choice(StealthBrowser.WEBGL_CONFIGS)
        concurrency = random.choice([4, 8, 12, 16])
        memory = random.choice([4, 8, 16])
        is_chrome = "Chrome" in ua
        context = await browser.new_context(
            user_agent=ua,
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"' if is_chrome else "",
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.google.com/"
            }
        )
        await context.add_init_script(f"""
            Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
            if (navigator.userAgent.includes('Chrome')) {{
                window.chrome = {{ runtime: {{}}, loadTimes: function() {{}}, csi: function() {{}}, app: {{}} }};
            }}
            const mockPlugins = [{{ name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }}];
            Object.defineProperty(navigator, 'plugins', {{ get: () => mockPlugins }});
            Object.defineProperty(navigator, 'languages', {{ get: () => ['es-ES', 'es', 'en-US', 'en'] }});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {concurrency} }});
            Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {memory} }});
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{webgl["vendor"]}';
                if (parameter === 37446) return '{webgl["renderer"]}';
                return getParameter.apply(this, arguments);
            }};
        """)
        return context

    @staticmethod
    async def human_scroll(page):
        for _ in range(random.randint(2, 5)):
            await page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(0.2, 0.8))

    @staticmethod
    async def wait_for_cloudflare_challenge(page, timeout=10000):
        try:
            challenge_selectors = ["#challenge-running", "#challenge-stage", ".cf-browser-verification", ".ray_id"]
            for selector in challenge_selectors:
                if await page.query_selector(selector):
                    await asyncio.sleep(5)
                    break
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except: pass

    @staticmethod
    async def is_blocked(page):
        try:
            content = (await page.content()).lower()
            blocked_indicators = [
                "cloudflare", "checking your browser", "challenge-running", 
                "captcha", "security check", "access denied", "robot check", 
                "unusual traffic", "turnstile", "web page blocked", "attack id", 
                "message id", "fortigate"
            ]
            return any(indicator in content for indicator in blocked_indicators)
        except: return False

class FirecrawlClient:
    BASE_URL = "https://api.firecrawl.dev/v1"
    def __init__(self):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        if not self.api_key: return {"status": "error", "message": "FIRECRAWL_API_KEY no configurada"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            data = {"url": url, "formats": ["markdown", "html"], "onlyMainContent": True}
            try:
                response = await client.post(f"{self.BASE_URL}/scrape", json=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e: return {"status": "error", "message": str(e)}

class FulltextRetriever:
    _user_home = os.path.expanduser("~")
    _docs_dir = "Documentos" if os.path.exists(os.path.join(_user_home, "Documentos")) else "Documents"

    UNPAYWALL_MCP_PATH = os.path.join(_user_home, _docs_dir, "Segon_Cervell/03_ESTUDI/03.1_TFM/unpaywall-mcp-local/dist/index.js")
    STORAGE_DIR = os.path.join(_user_home, _docs_dir, "Segon_Cervell/03_ESTUDI/03.1_TFM/articles_fulltext")

    @staticmethod
    def _get_cache_path(doi: str) -> str:
        safe_doi = re.sub(r'[^a-zA-Z0-9]', '_', doi)
        return os.path.join(FulltextRetriever.STORAGE_DIR, f"{safe_doi}.json")
    @staticmethod
    def check_cache(doi: str) -> Optional[Dict[str, Any]]:
        cache_path = FulltextRetriever._get_cache_path(doi)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return None
        return None
    @staticmethod
    def save_to_cache(doi: str, data: Dict[str, Any]):
        os.makedirs(FulltextRetriever.STORAGE_DIR, exist_ok=True)
        cache_path = FulltextRetriever._get_cache_path(doi)
        try:
            storage_data = {
                "doi": doi, "title": data.get("title", ""), "text": data.get("text", ""),
                "url": data.get("pdf_url") or data.get("url"), "metadata": data.get("metadata", {}),
                "download_date": datetime.now().isoformat(), "method": data.get("method", "unknown")
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
        except Exception as e: print(f"Error saving to cache: {e}")
    @staticmethod
    async def call_local_unpaywall_mcp(doi: str) -> Dict[str, Any]:
        try:
            request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "unpaywall_fetch_pdf_text", "arguments": {"doi": doi}}}
            env = os.environ.copy()
            if "UNPAYWALL_EMAIL" not in env: env["UNPAYWALL_EMAIL"] = "cavicas@alumni.uv.es"
            process = await asyncio.create_subprocess_exec("node", FulltextRetriever.UNPAYWALL_MCP_PATH, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
            stdout, stderr = await process.communicate(input=json.dumps(request).encode())
            if process.returncode != 0: return {"error": f"MCP failed: {stderr.decode()}"}
            response = json.loads(stdout.decode())
            if "error" in response: return {"error": response["error"]}
            tool_result = response.get("result", {}).get("content", [])
            if tool_result and tool_result[0].get("type") == "text": return json.loads(tool_result[0].get("text"))
            return {"error": "Unexpected format"}
        except Exception as e: return {"error": str(e)}

    async def retrieve(self, url: str, filename: Optional[str] = None) -> str:
        """Retrieves article full text by URL or DOI (checks cache and local Unpaywall first)."""
        is_doi = False
        doi_val = ""
        if "doi.org/" in url or (not url.startswith("http") and "/" in url):
            is_doi = True
            doi_val = url.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

        # 1. Check Cache
        if is_doi:
            cached = self.check_cache(doi_val)
            if cached:
                return json.dumps(cached, ensure_ascii=False)

        # 2. Try local Unpaywall MCP if it is a DOI and the file exists
        if is_doi and os.path.exists(self.UNPAYWALL_MCP_PATH):
            unpaywall_res = await self.call_local_unpaywall_mcp(doi_val)
            if isinstance(unpaywall_res, dict) and "error" not in unpaywall_res and unpaywall_res.get("text"):
                self.save_to_cache(doi_val, unpaywall_res)
                return json.dumps(unpaywall_res, ensure_ascii=False)

        # 3. Fallback to browser retrieval
        resolved_url = url
        if is_doi:
            resolved_url = f"https://doi.org/{doi_val}"

        browser_res = await self.retrieve_via_browser(resolved_url)
        if isinstance(browser_res, dict) and "error" not in browser_res and browser_res.get("text"):
            if is_doi:
                self.save_to_cache(doi_val, browser_res)
            return json.dumps(browser_res, ensure_ascii=False)

        error_msg = browser_res.get("error", "Unknown error") if isinstance(browser_res, dict) else str(browser_res)
        return json.dumps({"error": f"Failed to retrieve article content: {error_msg}"}, ensure_ascii=False)

    @staticmethod
    async def retrieve_via_browser(url: str) -> Dict[str, Any]:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await StealthBrowser.get_context(browser)
                page = await context.new_page()
                page.set_default_timeout(60000)
                
                print(f"Navegant a {url}...")
                
                # Intentem navegar. Si és un PDF directe, saltarà l'esdeveniment de download
                download_promise = page.wait_for_event("download", timeout=20000)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    # Esperem una mica més perquè es carreguin els scripts d'accés institucional
                    await asyncio.sleep(5)
                except Exception as ge:
                    if "Download is starting" not in str(ge) and "net::ERR_ABORTED" not in str(ge):
                        await browser.close()
                        return {"error": f"Error al carregar: {str(ge)}"}
                
                # ACEPTAR COOKIES (molt important per desbloquejar la pàgina)
                try:
                    cookie_selectors = [
                        "button:has-text('Accept')", "button:has-text('Agree')", 
                        "button:has-text('OK')", "button:has-text('Consiento')",
                        "#onetrust-accept-btn-handler", ".osano-cm-accept-all"
                    ]
                    for sel in cookie_selectors:
                        btn = await page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.click()
                            print("Cookies acceptades.")
                            await asyncio.sleep(1)
                            break
                except: pass

                # 1. Intentem detectar si s'ha disparat una descàrrega automàtica
                tmp_path = None
                try:
                    download = await download_promise
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp: tmp_path = tmp.name
                    await download.save_as(tmp_path)
                    print(f"Descàrrega automàtica detectada.")
                except:
                    # 2. Si no hi ha descàrrega automàtica, busquem el botó de PDF a la pàgina
                    print("Buscant botons de PDF a la pàgina...")
                    
                    # Llista de selectors intel·ligents per a les grans editorials
                    selectors = [
                        'a[data-track-action="download pdf"]',  # Springer
                        'a.c-pdf-download__link',                # Springer alternative
                        'a.btn-primary.content-download',        # IOP (Article PDF)
                        'a:has-text("Article PDF")',             # IOP alternative
                        'a[title="PDF"]',                        # ACS / General
                        'a.article-btn-pdf',                     # ACS specific
                        'a.pdf-link',                            # Wiley / ACS
                        '#pdf-link',                             # Elsevier / ScienceDirect
                        'a:has-text("Download PDF")',            # General English
                        'a:has-text("Descargar PDF")',           # General Spanish
                        'a:has-text(" PDF ")',                   # Generic PDF text
                        'img[alt*="Trobes"]',                    # UV Library Linker (Trobes) fallback
                        'a:has(img[alt*="Trobes"])'              # UV Library Linker link
                    ]
                    
                    found_btn = None
                    for selector in selectors:
                        try:
                            # Esperem un màxim de 3 segons per selector per no allargar-ho massa
                            btn = await page.wait_for_selector(selector, timeout=3000)
                            if btn:
                                found_btn = btn
                                print(f"Botó trobat amb el selector: {selector}")
                                break
                        except:
                            continue
                    
                    if found_btn:
                        # Si trobem el botó, li fem clic i esperem la descàrrega
                        try:
                            async with page.expect_download(timeout=30000) as download_info:
                                await found_btn.click()
                            download = await download_info.value
                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp: tmp_path = tmp.name
                            await download.save_as(tmp_path)
                            print("Descàrrega via clic completada.")
                        except Exception as ce:
                            print(f"Error al clicar el botó de PDF: {ce}")
                    
                    # FALLBACK: Cercador d'enllaços PDF genèric si res més ha funcionat
                    if not tmp_path:
                        print("Últim recurs: Buscant qualsevol enllaç que sembli un PDF...")
                        links = await page.query_selector_all("a[href]")
                        for link in links:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            if href and (".pdf" in href.lower() or "/pdf" in href.lower() or "pdf" in text.lower()):
                                try:
                                    async with page.expect_download(timeout=15000) as download_info:
                                        await link.click()
                                    download = await download_info.value
                                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp: tmp_path = tmp.name
                                    await download.save_as(tmp_path)
                                    print(f"Descàrrega aconseguida via link genèric: {href}")
                                    break
                                except: continue
                
                # 3. Processament final del fitxer
                await browser.close()
                
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        import pypdf
                        reader = pypdf.PdfReader(tmp_path)
                        text = "".join([p.extract_text() + "\n" for p in reader.pages])
                        os.unlink(tmp_path)
                        return {
                            "pdf_url": url,
                            "text": text,
                            "metadata": {
                                "n_pages": len(reader.pages),
                                "method": "browser_download_vpn"
                            }
                        }
                    except Exception as pe:
                        if os.path.exists(tmp_path): os.unlink(tmp_path)
                        return {"error": f"Error processant el PDF: {str(pe)}"}
                
                return {"error": "No s'ha pogut localitzar o descarregar el PDF oficial."}
        except Exception as e:
            return {"error": f"Error general del navegador: {str(e)}"}

class UnpaywallClient:
    """Unpaywall API - Finding legal open access PDFs by DOI."""
    BASE_URL = "https://api.unpaywall.org/v2"
    def __init__(self, email="cavicas@alumni.uv.es"):
        self.email = email
    async def get_pdf_url(self, doi: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.BASE_URL}/{doi}", params={"email": self.email})
                if response.status_code == 200:
                    data = response.json()
                    if data.get("is_oa"):
                        oa_locations = data.get("oa_locations", [])
                        for loc in oa_locations:
                            if loc.get("url_for_pdf"): return loc["url_for_pdf"]
                        return data.get("best_oa_location", {}).get("url_for_pdf")
            except: pass
        return None

class FulltextFinder:
    """Unified PDF discovery tool with conditional fallbacks."""
    
    async def find(self, doi: str, title: str = "") -> Dict[str, Any]:
        from .openalex import OpenAlexSearcher
        doi_clean = doi.replace("https://doi.org/", "").strip()
        results = {
            "doi": doi_clean,
            "official_url": None,
            "source_type": None,
            "fallbacks_needed": True
        }
        
        # 1. Check Unpaywall (Legal OA)
        up = UnpaywallClient()
        oa_url = await up.get_pdf_url(doi_clean)
        if oa_url:
            results["official_url"] = oa_url
            results["source_type"] = "Unpaywall (Open Access)"
            results["fallbacks_needed"] = False
            return results

        # 2. Check OpenAlex (Official Metadata/OA)
        oa = OpenAlexSearcher()
        try:
            work = await oa.get_work(doi_clean)
            if work.get("open_access", {}).get("is_oa"):
                oa_url = work.get("open_access", {}).get("oa_url")
                if oa_url:
                    results["official_url"] = oa_url
                    results["source_type"] = "OpenAlex (Official OA)"
                    results["fallbacks_needed"] = False
                    return results
        except Exception:
            pass

        # 3. Check CORE (Institutional Repositories)
        from .global_api import CoreSearcher
        core = CoreSearcher()
        try:
            core_results = await core.search(doi_clean or title, limit=1)
            if core_results and core_results[0].doi.lower() == doi_clean.lower():
                results["official_url"] = core_results[0].url
                results["source_type"] = "CORE (Institutional Repository)"
                results["fallbacks_needed"] = False
                return results
        except Exception:
            pass

        # 4. If no official OA found, prepare fallbacks
        results["researchgate_search"] = f"https://www.researchgate.net/search/publication?q={doi_clean or title}"
        results["fallbacks"] = {
            "sci_hub": f"https://sci-hub.se/{doi_clean}",
            "annas_archive": f"https://annas-archive.org/search?q={doi_clean or title}",
            "libgen": f"https://libgen.is/scimag/?q={doi_clean}"
        }
        return results
