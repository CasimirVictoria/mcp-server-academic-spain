#!/usr/bin/env python3
import sys
import os
import glob
import asyncio
import logging
import json
import re
import time
import math
from typing import List, Dict, Any, Optional

# --- Environment Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.join(project_root, "venv/lib/python3.*/site-packages")
paths = glob.glob(base_path)
if paths:
    sys.path.insert(0, paths[0])

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# --- Logging Configuration ---
import getpass
log_file = f"/tmp/mcp_academic_{getpass.getuser()}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("academic-spain-mcp")

def load_keys():
    try:
        from dotenv import load_dotenv
        keys_path = os.path.expanduser("~/.mcp_academic_keys")
        load_dotenv(keys_path, override=True)
        if os.getenv("SCOPUS_API_KEY"):
            logger.info(f"API keys loaded successfully from {keys_path}")
        else:
            logger.warning(f"API keys NOT found in {keys_path}")
    except Exception as e:
        logger.error(f"Failed to load API keys: {e}")

load_keys()

# Import our modular platforms
from platforms import (
    Paper, DialnetSearcher, RedinedSearcher, BOESearcher, 
    ProcomunSearcher, OpenAlexSearcher, ZenodoSearcher,
    SemanticScholarSearcher, GoogleScholarSearcher, ScieloSearcher,
    TeseoSearcher, GVASearcher, RodericSearcher,
    EricSearcher, EurekaSearcher, IntefSearcher,
    ArxivSearcher, CoreSearcher, PubMedSearcher, ScopusSearcher, WOSSearcher,
    TDRSearcher, RedalycSearcher, CrossRefSearcher, EuropePMCSearcher, HALSearcher, IACRSearcher,
    RiunetSearcher, RuaSearcher, UjiSearcher, RebiunSearcher,
    QueryExpander, FulltextRetriever
)

server = Server("academic-spain-education-mcp")

# --- Source Quality Scores (1-10) ---
# Keys MUST match exactly the 'source' strings set in each platform file.
# Used for deduplication: when the same paper appears in multiple sources,
# we keep the metadata from the highest-quality source.
# Also exposed in results as 'quality_score' field.
#
# NOTE: BOE, GVA (DOGV), Procomun and Redined are LEGISLATION / OER sources,
# not academic databases. They live in a separate category and are only
# useful when explicitly requested (e.g. curriculum laws, official norms).
# They score low so they never displace a real academic result in dedup.

SOURCE_QUALITY = {
    # --- ACADEMIC DATABASES ---

    # Tier 1 — Gold standard (rigorous peer-review indexing)
    "Scopus":              10,
    "Web of Science":      10,

    # Tier 2 — Excellent (highly curated, broad international coverage)
    "PubMed":               9,
    "EuropePMC":            9,
    "ERIC":                 9,   # gold standard for education research

    # Tier 3 — Very good (open, comprehensive, reliable)
    "Dialnet":              8,   # gold standard for Spanish-language academia
    "Semantic Scholar":     8,
    "OpenAlex":             8,
    "CrossRef":             8,
    "REBIUN":               8,   # national collective catalog
    "TDR (TDX)":            8,   # official Spanish thesis repository
    "TESEO":                8,   # official national thesis registry

    # Tier 4 — Good (peer-reviewed or institutional, narrower scope)
    "Redalyc":              7,
    "SciELO":               7,
    "RODERIC (UV)":         7,   # UV institutional repository
    "RIUNET (UPV)":         7,   # UPV institutional repository
    "RUA (UA)":             7,   # UA institutional repository
    "UJI Repositori":       7,   # UJI institutional repository
    "HAL (FR)":             7,
    "arXiv":                7,
    "CORE":                 6,
    "Zenodo":               6,
    "INTEF":                6,   # Spanish teacher resource portal

    # Tier 5 — General / aggregators (no quality filter)
    "GoogleScholar":        3,
    "RevistaEureka":        3,

    # --- LEGISLATION & OER (different category, not academic papers) ---
    "Redined":              2,   # Spanish education research network (mixed quality)
    "Procomun":             2,   # Spanish OER portal
    "GVA (DOGV)":           1,   # Valencian official gazette (legislation)
    "BOE":                  1,   # Spanish official gazette (legislation)
}

CACHE_FILE = os.path.expanduser("~/.mcp_academic_search_cache.json")
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")

SEARCH_CACHE = load_cache()

_INSTANTIATED_SEARCHERS = {}
SEARCHER_CLASSES = {
    "dialnet": DialnetSearcher,
    "redined": RedinedSearcher,
    "boe": BOESearcher,
    "procomun": ProcomunSearcher,
    "openalex": OpenAlexSearcher,
    "zenodo": ZenodoSearcher,
    "semanticscholar": SemanticScholarSearcher,
    "googlescholar": GoogleScholarSearcher,
    "scielo": ScieloSearcher,
    "teseo": TeseoSearcher,
    "gva": GVASearcher,
    "roderic": RodericSearcher,
    "riunet": RiunetSearcher,
    "rua": RuaSearcher,
    "uji": UjiSearcher,
    "rebiun": RebiunSearcher,
    "intef": IntefSearcher,
    "eric": EricSearcher,
    "eureka": EurekaSearcher,
    "arxiv": ArxivSearcher,
    "core": CoreSearcher,
    "pubmed": PubMedSearcher,
    "scopus": ScopusSearcher,
    "wos": WOSSearcher,
    "tdr": TDRSearcher,
    "redalyc": RedalycSearcher,
    "crossref": CrossRefSearcher,
    "europepmc": EuropePMCSearcher,
    "hal": HALSearcher,
    "iacr": IACRSearcher
}

def get_searcher(name):
    if name not in _INSTANTIATED_SEARCHERS and name in SEARCHER_CLASSES:
        _INSTANTIATED_SEARCHERS[name] = SEARCHER_CLASSES[name]()
    return _INSTANTIATED_SEARCHERS.get(name)

query_expander = QueryExpander()
retriever = FulltextRetriever()

# --- VPN (eduVPN / WireGuard via NetworkManager) ---
VPN_CONNECTION_NAME = os.getenv("VPN_CONNECTION_NAME", "eduVPN")

async def vpn_is_active() -> bool:
    """Returns True if the eduVPN WireGuard connection is currently active."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "-t", "-f", "NAME,STATE", "con", "show", "--active",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await proc.communicate()
        return VPN_CONNECTION_NAME.lower() in stdout.decode().lower()
    except Exception:
        return False

async def vpn_connect() -> Dict[str, Any]:
    """Connects eduVPN via NetworkManager. Returns status dict."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "con", "up", VPN_CONNECTION_NAME,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        success = proc.returncode == 0
        return {
            "connected": success,
            "message": stdout.decode().strip() or stderr.decode().strip()
        }
    except asyncio.TimeoutError:
        return {"connected": False, "message": "Timeout: la connexió VPN ha trigat massa"}
    except Exception as e:
        return {"connected": False, "message": str(e)}

async def vpn_disconnect() -> Dict[str, Any]:
    """Disconnects eduVPN via NetworkManager."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "con", "down", VPN_CONNECTION_NAME,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        success = proc.returncode == 0
        return {
            "disconnected": success,
            "message": stdout.decode().strip() or stderr.decode().strip()
        }
    except Exception as e:
        return {"disconnected": False, "message": str(e)}

def clean_and_reconstruct_abstract(abstract_val: Any) -> str:
    if not abstract_val:
        return ""
    if isinstance(abstract_val, dict):
        try:
            positions = []
            for word, idxs in abstract_val.items():
                if isinstance(idxs, list):
                    for idx in idxs:
                        positions.append((idx, word))
            positions.sort()
            return " ".join([word for _, word in positions])
        except Exception as e:
            logger.error(f"Error reconstructing abstract dict: {e}")
            return ""
    if isinstance(abstract_val, str):
        val_strip = abstract_val.strip()
        if val_strip.startswith("{") and val_strip.endswith("}"):
            try:
                import json
                parsed = json.loads(val_strip)
                if isinstance(parsed, dict):
                    return clean_and_reconstruct_abstract(parsed)
            except Exception:
                pass
        return val_strip
    return str(abstract_val)

def get_paper_key(paper: Paper) -> str:
    if paper.doi:
        doi = paper.doi.lower().strip()
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        return f"doi:{doi}"
    # Keep only alphanumeric characters for title matching
    title_val = paper.title or ""
    title_norm = re.sub(r'[^a-z0-9]', '', title_val.lower())
    return f"title:{title_norm}"

def get_quality_score(paper: Paper) -> int:
    """Return the quality score of the paper's source (0 if unknown)."""
    sources = [s.strip() for s in paper.source.split(",")]
    scores = [SOURCE_QUALITY.get(s, 0) for s in sources]
    return max(scores) if scores else 0

def compute_relevance_score(paper: Paper, query: str) -> float:
    """Calcula un score de rellevància del paper d'1 a 100 ponderant diversos factors."""
    # 1. Coincidència lèxica (Títol i Abstract) - Màxim 40 punts
    lexical_score = 0.0
    query_cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
    keywords = [w for w in query_cleaned.split() if len(w) > 3]
    
    if keywords:
        title_lower = paper.title.lower() if paper.title else ""
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        title_matches = sum(1 for kw in keywords if kw in title_lower)
        abstract_matches = sum(1 for kw in keywords if kw in abstract_lower)
        
        # Bonus per frase exacta o consecutiva al títol
        query_phrase = " ".join(keywords)
        phrase_bonus = 10.0 if query_phrase in title_lower else 0.0
        
        title_factor = (title_matches / len(keywords)) * 30.0 + phrase_bonus
        abstract_factor = (abstract_matches / len(keywords)) * 10.0
        
        lexical_score = min(40.0, title_factor + abstract_factor)
    else:
        lexical_score = 10.0  # base
        
    # 2. Qualitat de la Font - Màxim 30 punts
    source_score = SOURCE_QUALITY.get(paper.source, 0) * 3.0
    
    # 3. Citacions (Impacte logarítmic) - Màxim 20 punts
    citations = getattr(paper, "citations", 0) or 0
    citations_score = min(20.0, math.log1p(citations) * 4.0)
    
    # 4. Any de publicació (Novetat) - Màxim 10 punts
    recency_score = 1.0
    pub_date = getattr(paper, "published_date", "") or ""
    year_match = re.search(r'\b(19|20)\d{2}\b', str(pub_date))
    if year_match:
        year = int(year_match.group(0))
        if year >= 2024:
            recency_score = 10.0
        elif year >= 2021:
            recency_score = 8.0
        elif year >= 2018:
            recency_score = 5.0
        elif year >= 2015:
            recency_score = 3.0
        else:
            recency_score = 1.5
            
    total_score = lexical_score + source_score + citations_score + recency_score
    return round(total_score, 2)

def format_rich_output(papers: List[Paper], query: str, requested_sources: str) -> str:
    """Format els resultats de cerca en un document Markdown preciós i net (tipus biomcp)."""
    if not papers:
        return f"### 🔍 No s'ha trobat cap article per a la cerca: *\"{query}\"*\n\nIntenta simplificar la consulta o utilitzar altres fonts."
        
    markdown = []
    markdown.append(f"# 🔬 Resultats de Cerca Acadèmica (`tfm-search`)")
    markdown.append(f"**Consulta:** *\"{query}\"* | **Fonts:** `{requested_sources}`")
    markdown.append(f"**Rànquing aplicat:** Rellevància Híbrida (Lexical + Qualitat Font + Citacions + Recency)\n")
    
    # Taula de resultats
    markdown.append("| # | Puntuació | Títol de l'Article | Autors | Font (Score) | Any | Cit. | Accés / DOI |")
    markdown.append("|---|---|---|---|---|---|---|---|")
    
    for idx, paper in enumerate(papers, 1):
        title = paper.title.replace("|", "\\|").strip() if paper.title else "Sense títol"
        if paper.url:
            title_link = f"[{title}]({paper.url})"
        else:
            title_link = title
            
        authors_list = paper.authors if paper.authors else []
        if not authors_list:
            authors_str = "Desconegut"
        elif len(authors_list) == 1:
            authors_str = authors_list[0]
        elif len(authors_list) <= 3:
            authors_str = ", ".join(authors_list[:-1]) + " & " + authors_list[-1]
        else:
            authors_str = authors_list[0] + " et al."
        authors_str = authors_str.replace("|", "\\|")
            
        source_quality = get_quality_score(paper)
        source_str = f"{paper.source} ({source_quality})"
        
        year = "-"
        pub_date = getattr(paper, "published_date", "") or ""
        year_match = re.search(r'\b(19|20)\d{2}\b', str(pub_date))
        if year_match:
            year = year_match.group(0)
            
        citations = getattr(paper, "citations", 0) or 0
        cit_str = str(citations) if citations > 0 else "0"
        
        links = []
        if paper.pdf_url:
            links.append(f"🔓 [PDF]({paper.pdf_url})")
        if paper.doi:
            doi_url = paper.doi if paper.doi.startswith("http") else f"https://doi.org/{paper.doi}"
            links.append(f"🔗 [DOI]({doi_url})")
            
        links_str = " / ".join(links) if links else "Sense enllaç"
        score = getattr(paper, "ranking_score", 0.0)
        
        markdown.append(f"| {idx} | **{score}** | {title_link} | {authors_str} | {source_str} | {year} | {cit_str} | {links_str} |")
        
    markdown.append("\n---\n")
    
    # Resums dels 3 primers articles
    markdown.append("## 📄 Resums dels Articles més Rellevants\n")
    top_papers = papers[:3]
    for idx, paper in enumerate(top_papers, 1):
        title = paper.title.strip() if paper.title else "Sense títol"
        abstract = paper.abstract.strip() if getattr(paper, "abstract", None) else "No hi ha resum disponible."
        if isinstance(abstract, dict) or str(abstract).startswith("{"):
            abstract = "Resum en format no suportat."
        
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
            
        authors_list = paper.authors if paper.authors else []
        authors_str = ", ".join(authors_list) if authors_list else "Desconegut"
        
        markdown.append(f"### {idx}. {title}")
        markdown.append(f"**Autors:** *{authors_str}* | **Font:** *{paper.source}*")
        markdown.append(f"> {abstract}\n")
        
    markdown.append("---\n")
    
    # Comandes d'acció ràpida (VPN i Zotero)
    markdown.append("## 💡 Recomanacions i Integració Directa\n")
    
    has_doi = False
    for paper in papers[:5]:
        if paper.doi:
            has_doi = True
            doi_clean = paper.doi.replace("https://doi.org/", "")
            markdown.append(f"- **Afegir a Zotero:** `mcp_zotero_zotero_add_by_doi(doi=\"{doi_clean}\")` per a l'article *\"{paper.title}\"*")
            
    if not has_doi:
        markdown.append("- **Afegir a Zotero:** Cap dels articles recents té DOI directe. Pots afegir-los mitjançant la URL o manualment.")
        
    has_paywall = any(p.source in ["Scopus", "Web of Science"] for p in papers[:5])
    if has_paywall:
        markdown.append("- **Accés UV eduVPN:** S'han detectat articles de Scopus o WOS. Recorda connectar la VPN institucional amb `vpn_control(action=\"connect\")` per a poder accedir-hi completament.")
    else:
        markdown.append("- **Descàrrega directa:** Pots descarregar els PDFs d'accés obert directament des dels enllaços de la taula superior.")
        
    return "\n".join(markdown)

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    sources_desc = ", ".join(SEARCHER_CLASSES.keys())
    return [
        types.Tool(
            name="search_academic_spain",
            description=f"Search across multiple Spanish and global academic sources ({sources_desc}).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sources": {"type": "string", "description": "Comma-separated list of sources or 'all'"},
                    "limit": {"type": "integer", "default": 5},
                    "expand_query": {"type": "boolean", "default": False},
                    "output_format": {
                        "type": "string",
                        "enum": ["rich", "json"],
                        "default": "rich",
                        "description": "Output format: 'rich' for a beautiful Markdown table and research insights (default), or 'json' for raw structured data."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="download_paper",
            description=(
                "Download the full text of a paper. Tries Unpaywall (OA) first, "
                "then browser-based download. If the article is paywalled, "
                "connecting the UV eduVPN gives institutional access. "
                "Set auto_vpn=true to connect automatically before downloading."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL or DOI of the paper"},
                    "filename": {"type": "string", "description": "Optional filename to save as"},
                    "auto_vpn": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, auto-connect eduVPN before attempting download"
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="vpn_control",
            description=(
                "Control the UV eduVPN (WireGuard via NetworkManager). "
                "Use to check status, connect, or disconnect the institutional VPN "
                "which gives access to Scopus, WOS, and subscribed journals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "connect", "disconnect"],
                        "description": "'status' to check, 'connect' to activate, 'disconnect' to deactivate"
                    }
                },
                "required": ["action"]
            }
        ),
        types.Tool(
            name="unified_search",
            description=(
                "Unified academic search with smart query routing and deduplication. "
                "Automatically queries Spanish, clinical/biomedical, and global databases "
                "based on the query intent. Merges and ranks the results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 5, "description": "Max results to return"},
                    "category": {
                        "type": "string",
                        "enum": ["all", "general", "education", "biomedical", "spanish"],
                        "default": "all",
                        "description": "Override query classification and route to specific source groups"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["rich", "json"],
                        "default": "rich",
                        "description": "Output format: 'rich' (Markdown table) or 'json' (raw data)"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    if name == "unified_search":
        query = arguments.get("query")
        limit = arguments.get("limit", 5)
        category = arguments.get("category", "all")
        output_format = arguments.get("output_format", "rich")

        # Smart Category Routing
        if category == "all":
            query_lower = query.lower()
            # Detect biomedical query
            biomedical_keywords = ["gen", "gene", "dna", "rna", "protein", "cancer", "disease", "drug", "cell", "biomedical", "clinical", "paciente", "médico", "cáncer", "fármaco", "vacuna"]
            # Detect Spanish education / TFM query
            spanish_edu_keywords = ["lomloe", "valencia", "gva", "secundaria", "primaria", "aula", "didáctica", "didactica", "docente", "aprendizaje", "aprenentatge", "educación", "educació", "escuela", "escola", "colegio", "col·legi"]
            
            if any(kw in query_lower for kw in biomedical_keywords):
                category = "biomedical"
            elif any(kw in query_lower for kw in spanish_edu_keywords):
                category = "spanish_education"
            else:
                category = "general"

        logger.info(f"Unified Search: classified query '{query}' as category '{category}'")

        # Map categories to sources
        if category == "biomedical":
            source_list = ["pubmed", "europepmc", "semanticscholar", "openalex"]
        elif category == "spanish_education":
            source_list = ["dialnet", "redined", "eric", "eureka", "openalex", "intef", "riunet", "rua", "uji"]
        elif category == "spanish":
            source_list = ["dialnet", "redined", "scielo", "tdr", "roderic", "riunet", "rua", "uji"]
        elif category == "education":
            source_list = ["eric", "redined", "eureka", "openalex", "intef"]
        else: # general
            source_list = ["openalex", "semanticscholar", "crossref", "dialnet", "arxiv", "rebiun"]

        # Run search
        tasks = []
        for s_name in source_list:
            searcher = get_searcher(s_name)
            if searcher:
                tasks.append(asyncio.wait_for(searcher.search(query, limit=limit), timeout=25.0))

        if not tasks:
            return [types.TextContent(type="text", text="No valid sources found for the resolved category.")]

        logger.info(f"Starting unified search across {len(source_list)} sources for query: {query}")
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: Dict[str, Paper] = {}
        for idx, res_list in enumerate(search_results):
            s_name = source_list[idx]
            if isinstance(res_list, list):
                for paper in res_list:
                    paper.abstract = clean_and_reconstruct_abstract(paper.abstract)
                    key = get_paper_key(paper)
                    
                    if key not in all_results:
                        all_results[key] = paper
                    else:
                        # Combine authors if missing or if one list is longer
                        existing = all_results[key]
                        if len(paper.authors) > len(existing.authors):
                            existing.authors = paper.authors
                        if not existing.doi and paper.doi:
                            existing.doi = paper.doi
                        if not existing.abstract and paper.abstract:
                            existing.abstract = paper.abstract
                        if not existing.pdf_url and paper.pdf_url:
                            existing.pdf_url = paper.pdf_url
                        
                        # Merge source lists
                        sources = [s.strip() for s in existing.source.split(",")]
                        if paper.source not in sources:
                            sources.append(paper.source)
                        existing.source = ", ".join(sources)
            elif isinstance(res_list, Exception):
                logger.error(f"Unified search task for '{s_name}' failed: {res_list}")

        # Compute ranking score for all results and sort
        sorted_papers = list(all_results.values())
        for p in sorted_papers:
            p.ranking_score = compute_relevance_score(p, query)

        sorted_papers.sort(key=lambda x: x.ranking_score, reverse=True)

        # Truncate to limit after sorting and deduplication
        sorted_papers = sorted_papers[:limit]

        # Prepare JSON payload structured list
        results_data = []
        for p in sorted_papers:
            d = p.__dict__.copy()
            d["quality_score"] = get_quality_score(p)
            d["ranking_score"] = p.ranking_score
            results_data.append(d)

        if output_format == "json":
            return [types.TextContent(type="text", text=json.dumps(results_data, indent=2, ensure_ascii=False))]
        else:
            rich_text = format_rich_output(sorted_papers, query, ", ".join(source_list))
            return [types.TextContent(type="text", text=rich_text)]

    elif name == "search_academic_spain":
        query = arguments.get("query")
        limit = arguments.get("limit", 5)
        requested_sources = arguments.get("sources", "all")
        expand = arguments.get("expand_query", False)
        output_format = arguments.get("output_format", "rich")
        
        # Check cache (caching structured data list)
        cache_key = f"{query}_{limit}_{requested_sources}_{expand}"
        cached_data = None
        if cache_key in SEARCH_CACHE:
            entry = SEARCH_CACHE[cache_key]
            if isinstance(entry, dict) and "timestamp" in entry and time.time() - entry["timestamp"] < 7 * 86400:
                logger.info(f"Returning cached results for {query}")
                cached_data = entry["data"]
        
        if cached_data is not None:
            # Sanejament en calent de dades antigues recuperades de la cache
            for p_dict in cached_data:
                if "abstract" in p_dict:
                    p_dict["abstract"] = clean_and_reconstruct_abstract(p_dict["abstract"])
            
            if output_format == "json":
                return [types.TextContent(type="text", text=json.dumps(cached_data, indent=2, ensure_ascii=False))]
            else:
                papers = [Paper(**p_dict) for p_dict in cached_data]
                for p in papers:
                    if not hasattr(p, "ranking_score"):
                        p.ranking_score = compute_relevance_score(p, query)
                # Sort descending by relevance score
                papers.sort(key=lambda x: getattr(x, "ranking_score", 0.0), reverse=True)
                rich_text = format_rich_output(papers, query, requested_sources)
                return [types.TextContent(type="text", text=rich_text)]
        
        queries = [query]
        if expand:
            queries.extend(query_expander.expand(query))
        
        all_results: Dict[str, Paper] = {}
        
        # Nucli de fonts Core super ràpides i robustes per al context del TFM Educatiu
        core_sources = ["openalex", "dialnet", "semanticscholar", "eric", "europepmc", "arxiv", "rebiun", "intef"]
        
        if requested_sources == "all":
            # Comprovació asíncrona de l'estat de la VPN (necessària per a Scopus / WOS)
            vpn_active = await vpn_is_active()
            scopus_key = os.getenv("SCOPUS_API_KEY")
            
            # Només afegim les de subscripció premium si la VPN està connectada i tenim claus API
            if vpn_active and scopus_key:
                logger.info("eduVPN activa i clau API de Scopus trobada. S'afegeixen Scopus i WOS a la cerca.")
                core_sources.append("scopus")
                core_sources.append("wos")
            else:
                logger.info("eduVPN inactiva o clau de Scopus absent. Cerca ràpida Core-only activada.")
                
            source_list = core_sources
        else:
            source_list = [s.strip().lower() for s in requested_sources.split(",")]
        
        tasks = []
        for q in queries:
            for s_name in source_list:
                searcher = get_searcher(s_name)
                if searcher:
                    tasks.append(asyncio.wait_for(searcher.search(q, limit=limit), timeout=20.0))
        
        if not tasks:
            return [types.TextContent(type="text", text="No valid sources requested.")]
 
        logger.info(f"Starting search across {len(source_list)} sources for query: {query}")
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, res_list in enumerate(search_results):
            if isinstance(res_list, list):
                for paper in res_list:
                    # Sanegem en calent l'abstract del nou paper abans de cap rellevància
                    paper.abstract = clean_and_reconstruct_abstract(paper.abstract)
                    
                    key = get_paper_key(paper)
                    if key not in all_results:
                        all_results[key] = paper
                    else:
                        # Deduplication: keep the result from the highest-quality source
                        existing_score = get_quality_score(all_results[key])
                        new_score = get_quality_score(paper)
                        if new_score > existing_score:
                            old_source = all_results[key].source
                            all_results[key] = paper
                            logger.info(f"Replaced '{old_source}' (score={existing_score}) "
                                        f"with '{paper.source}' (score={new_score}) "
                                        f"for key: {key}")
            elif isinstance(res_list, Exception):
                logger.error(f"Search task failed: {res_list}")

        # Compute ranking score for all results and sort
        sorted_papers = list(all_results.values())
        for p in sorted_papers:
            p.ranking_score = compute_relevance_score(p, query)
            
        sorted_papers.sort(key=lambda x: x.ranking_score, reverse=True)

        # Prepare cache / JSON payload structured list
        results_data = []
        for p in sorted_papers:
            d = p.__dict__.copy()
            d["quality_score"] = get_quality_score(p)
            d["ranking_score"] = p.ranking_score
            results_data.append(d)

        SEARCH_CACHE[cache_key] = {"timestamp": time.time(), "data": results_data}
        save_cache(SEARCH_CACHE)
        
        if output_format == "json":
            return [types.TextContent(type="text", text=json.dumps(results_data, indent=2, ensure_ascii=False))]
        else:
            rich_text = format_rich_output(sorted_papers, query, requested_sources)
            return [types.TextContent(type="text", text=rich_text)]

    elif name == "download_paper":
        url = arguments.get("url")
        filename = arguments.get("filename")
        auto_vpn = arguments.get("auto_vpn", False)

        vpn_was_active = await vpn_is_active()
        vpn_connected_now = False

        # Auto-connect VPN if requested and not already active
        if auto_vpn and not vpn_was_active:
            logger.info("auto_vpn=True: connecting eduVPN before download...")
            conn_result = await vpn_connect()
            vpn_connected_now = conn_result["connected"]
            if vpn_connected_now:
                logger.info("eduVPN connected successfully")
                await asyncio.sleep(2)  # let routing stabilize
            else:
                logger.warning(f"VPN auto-connect failed: {conn_result['message']}")

        res = await retriever.retrieve(url, filename)

        # Annotate result with VPN context
        try:
            result_dict = json.loads(res) if isinstance(res, str) else res
        except Exception:
            result_dict = {"raw": res}

        vpn_active_now = await vpn_is_active()
        result_dict["vpn_status"] = {
            "was_active_before": vpn_was_active,
            "auto_connect_attempted": auto_vpn and not vpn_was_active,
            "active_during_download": vpn_active_now,
            "hint": (
                None if vpn_active_now
                else "⚠️ La VPN (eduVPN) estava desconnectada. "
                     "Articles de pagament de Scopus/WOS/editorials poden no ser accessibles. "
                     "Connecta-la i reintenta, o usa auto_vpn=true."
            )
        }

        return [types.TextContent(type="text", text=json.dumps(result_dict, ensure_ascii=False, indent=2))]

    elif name == "vpn_control":
        action = arguments.get("action", "status")
        if action == "status":
            active = await vpn_is_active()
            return [types.TextContent(type="text", text=json.dumps({
                "vpn": VPN_CONNECTION_NAME,
                "active": active,
                "status": "🟢 Connectada — accés institucional UV actiu" if active
                          else "🔴 Desconnectada — només Open Access disponible"
            }, ensure_ascii=False))]
        elif action == "connect":
            if await vpn_is_active():
                return [types.TextContent(type="text", text=json.dumps(
                    {"connected": True, "message": "La VPN ja estava activa"}, ensure_ascii=False))]
            result = await vpn_connect()
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        elif action == "disconnect":
            if not await vpn_is_active():
                return [types.TextContent(type="text", text=json.dumps(
                    {"disconnected": True, "message": "La VPN ja estava desconnectada"}, ensure_ascii=False))]
            result = await vpn_disconnect()
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        else:
            return [types.TextContent(type="text", text=json.dumps(
                {"error": f"Acció desconeguda: {action}. Usa 'status', 'connect' o 'disconnect'"}))]

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "stdio":
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="academic-spain-mcp",
                    server_version="2.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    else:
        # SSE implementation if needed
        pass

if __name__ == "__main__":
    asyncio.run(main())
