import os
import httpx
import logging
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base import PaperSource
from .models import Paper

logger = logging.getLogger("academic-spain-mcp")

class ArxivSearcher(PaperSource):
    """arXiv API - Open Access Preprints."""
    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": limit,
                    "sortBy": "relevance",
                    "sortOrder": "descending"
                }
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    return []
                
                root = ET.fromstring(response.text)
                ns = {'ns': 'http://www.w3.org/2005/Atom'}
                
                output = []
                for entry in root.findall('ns:entry', ns):
                    title_el = entry.find('ns:title', ns)
                    title = title_el.text.strip().replace('\n', ' ') if title_el is not None else "N/A"
                    
                    id_el = entry.find('ns:id', ns)
                    url = id_el.text.strip() if id_el is not None else "https://arxiv.org/"
                    
                    published_el = entry.find('ns:published', ns)
                    published = published_el.text.strip() if published_el is not None else "N/A"
                    year = published[:4] if published != "N/A" else "N/A"
                    
                    authors = []
                    for author in entry.findall('ns:author', ns):
                        name_el = author.find('ns:name', ns)
                        if name_el is not None:
                            authors.append(name_el.text.strip())
                        
                    doi = ""
                    for link in entry.findall('ns:link', ns):
                        if link.get('title') == 'doi':
                            doi = link.get('href', '').replace('http://dx.doi.org/', '')
                            
                    output.append(Paper(
                        paper_id=url.split('/')[-1],
                        title=title,
                        authors=authors,
                        published_date=year,
                        url=url,
                        doi=doi,
                        source="arXiv"
                    ))
                return output
            except Exception:
                return []

class CoreSearcher(PaperSource):
    """CORE API - Aggregates global Open Access content."""
    BASE_URL = "https://api.core.ac.uk/v3/search/works"
    
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        api_key = os.getenv("CORE_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                params = {"q": query, "limit": limit}
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                if response.status_code != 200:
                    return []
                
                data = response.json()
                results = data.get("results", [])
                output = []
                for item in results:
                    authors = []
                    for author in item.get("authors", []):
                        if isinstance(author, dict) and "name" in author:
                            authors.append(author["name"])
                        elif isinstance(author, str):
                            authors.append(author)
                            
                    download_url = item.get("downloadUrl", "")
                    url = download_url if download_url else item.get("sourceFulltextUrls", ["https://core.ac.uk/"])[0]
                    
                    output.append(Paper(
                        paper_id=str(item.get("id", "")),
                        title=item.get("title", "N/A"),
                        authors=authors,
                        published_date=str(item.get("yearPublished", "N/A")),
                        url=url,
                        doi=item.get("doi", ""),
                        source="CORE"
                    ))
                return output
            except Exception:
                return []

class PubMedSearcher(PaperSource):
    """PubMed API - Biomedical literature (NCBI)."""
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={limit}&retmode=json"
                res = await client.get(search_url)
                if res.status_code != 200: return []
                
                ids = res.json().get("esearchresult", {}).get("idlist", [])
                if not ids: return []
                
                id_str = ",".join(ids)
                sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={id_str}&retmode=json"
                res2 = await client.get(sum_url)
                if res2.status_code != 200: return []
                
                result_data = res2.json().get("result", {})
                output = []
                for uid in ids:
                    item = result_data.get(uid, {})
                    if not item: continue
                    
                    authors = [a.get("name") for a in item.get("authors", []) if "name" in a]
                    doi = next((aid.get("value") for aid in item.get("articleids", []) if aid.get("idtype") == "doi"), "")
                    
                    output.append(Paper(
                        paper_id=uid,
                        title=item.get("title", ""),
                        authors=authors,
                        published_date=item.get("pubdate", "")[:4],
                        journal=item.get("fulljournalname", ""),
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        doi=doi,
                        source="PubMed"
                    ))
                return output
            except Exception:
                return []

class ScopusSearcher(PaperSource):
    """Scopus API - Elsevier Research Database (API Key Required)."""
    BASE_URL = "https://api.elsevier.com/content/search/scopus"
    
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        api_key = os.getenv("SCOPUS_API_KEY", "")
        if not api_key:
            logger.warning("SCOPUS_API_KEY is empty in ScopusSearcher!")
            return []
        else:
            logger.info(f"SCOPUS_API_KEY found (starts with: {api_key[:4]}...)")
            
        headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                params = {"query": f"TITLE-ABS-KEY({query})", "count": limit}
                logger.info(f"Searching Scopus with query: {params['query']}")
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                logger.info(f"Scopus response status: {response.status_code}")
                
                if response.status_code != 200: 
                    logger.error(f"Scopus error: {response.text}")
                    return []
                
                data = response.json()
                entries = data.get("search-results", {}).get("entry", [])
                logger.info(f"Scopus found {len(entries)} entries")
                
                output = []
                for item in entries:
                    if "error" in item: continue
                    
                    doi = item.get("prism:doi", "")
                    url = next((link.get("@href") for link in item.get("link", []) if link.get("@ref") == "scopus"), f"https://doi.org/{doi}" if doi else "https://www.scopus.com/")
                    
                    output.append(Paper(
                        paper_id=doi or item.get("dc:identifier", ""),
                        title=item.get("dc:title", "N/A"),
                        authors=[item.get("dc:creator", "N/A")],
                        published_date=item.get("prism:coverDate", "N/A")[:4],
                        journal=item.get("prism:publicationName", ""),
                        citation_count=int(item.get("citedby-count", 0)),
                        url=url,
                        doi=doi,
                        source="Scopus"
                    ))
                return output
            except Exception as e:
                logger.error(f"Scopus search failed: {e}")
                return []

class WOSSearcher(PaperSource):
    """Web of Science (WOS) Starter API - Clarivate."""
    BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/search"
    
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Paper]:
        api_key = os.getenv("WOS_API_KEY", "")
        if not api_key:
            logger.warning("WOS_API_KEY is empty in WOSSearcher!")
            return []
            
        headers = {"X-ApiKey": api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                params = {"q": query, "limit": limit, "page": 1}
                logger.info(f"Searching WOS with query: {query}")
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                logger.info(f"WOS response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"WOS error: {response.text}")
                    return []
                
                hits = response.json().get("hits", [])
                logger.info(f"WOS found {len(hits)} hits")
                
                output = []
                for item in hits:
                    source_info = item.get("source", {})
                    pub_date = item.get("pubDate", "N/A")
                    authors = [a.get("displayName", "N/A") for a in item.get("names", {}).get("authors", [])]
                    
                    output.append(Paper(
                        paper_id=item.get("uid", item.get("title", "")),
                        title=item.get("title", "N/A"),
                        authors=authors,
                        published_date=pub_date[:4] if pub_date != "N/A" else "N/A",
                        journal=source_info.get("title", "N/A"),
                        url=item.get("links", {}).get("record", "https://www.webofscience.com/"),
                        source="Web of Science"
                    ))
                return output
            except Exception as e:
                logger.error(f"WOS search failed: {e}")
                return []

class CrossRefSearcher(PaperSource):
    """CrossRef API for DOI-based metadata lookup and search."""
    BASE_URL = "https://api.crossref.org"

    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"query": query, "rows": limit, "sort": "relevance"}
            try:
                response = await client.get(f"{self.BASE_URL}/works", params=params)
                response.raise_for_status()
                items = response.json().get("message", {}).get("items", [])
                output = []
                for item in items:
                    authors_raw = item.get("author", [])
                    authors_list = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_raw]
                    title = item.get("title", ["Sense títol"])[0]
                    journal = item.get("container-title", [""])[0]
                    doi = item.get("DOI", "")
                    # Extract year
                    year = None
                    for date_field in ["published-print", "published-online", "created"]:
                        dp = item.get(date_field, {}).get("date-parts", [[]])
                        if dp and dp[0]:
                            year = dp[0][0]
                            break
                    
                    output.append(Paper(
                        paper_id=doi,
                        title=title,
                        authors=authors_list,
                        year=year,
                        doi=f"https://doi.org/{doi}" if doi else None,
                        url=f"https://doi.org/{doi}" if doi else None,
                        journal=journal,
                        source="CrossRef"
                    ))
                return output
            except Exception:
                return []

class EuropePMCSearcher(PaperSource):
    """Europe PMC - open access biomedical and education literature."""
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"query": query, "resultType": "core", "pageSize": limit, "format": "json"}
            try:
                response = await client.get(f"{self.BASE_URL}/search", params=params)
                response.raise_for_status()
                results = response.json().get("resultList", {}).get("result", [])
                output = []
                for item in results:
                    authors_list = []
                    for a in (item.get("authorList", {}).get("author", []) or []):
                        name = f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                        if name: authors_list.append(name)
                    doi = item.get("doi", "")
                    year = item.get("pubYear")
                    output.append(Paper(
                        paper_id=item.get("id"),
                        title=item.get("title", ""),
                        authors=authors_list,
                        year=int(year) if year and year.isdigit() else None,
                        doi=f"https://doi.org/{doi}" if doi else None,
                        url=f"https://doi.org/{doi}" if doi else item.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url", ""),
                        journal=item.get("journalTitle", ""),
                        source="EuropePMC"
                    ))
                return output
            except Exception:
                return []
class HALSearcher(PaperSource):
    """HAL - French Open Access Archive."""
    BASE_URL = "https://api.archives-ouvertes.fr/search/"
    
    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "q": query,
                    "rows": limit,
                    "fl": "docid,label_s,uri_s,authFullName_s,producedDate_s,abstract_s,doi_s"
                }
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200: return []
                
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                
                output = []
                for doc in docs:
                    output.append(Paper(
                        paper_id=str(doc.get("docid")),
                        title=doc.get("label_s", "N/A"),
                        authors=doc.get("authFullName_s", []),
                        published_date=doc.get("producedDate_s", "N/A"),
                        abstract=doc.get("abstract_s", ""),
                        url=doc.get("uri_s", ""),
                        doi=doc.get("doi_s", [None])[0] if isinstance(doc.get("doi_s"), list) else None,
                        source="HAL (FR)"
                    ))
                return output
            except Exception: return []

class IACRSearcher(PaperSource):
    """IACR - International Association for Cryptologic Research (ePrint)."""
    BASE_URL = "https://eprint.iacr.org/search"
    
    async def search(self, query: str, limit: int = 5) -> List[Paper]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"q": query}
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200: return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select(".pub-container") 
                
                output = []
                return output
            except Exception: return []
