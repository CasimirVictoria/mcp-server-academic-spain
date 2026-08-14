import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger("academic-spain-mcp")

def clean_and_reconstruct_abstract(abstract_val: Any) -> str:
    """Sanitizes and reconstructs inverted index abstract formats into clean, human-readable strings."""
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
            logger.error(f"Error reconstructing abstract dict in models.py: {e}")
            return ""
    if isinstance(abstract_val, str):
        val_strip = abstract_val.strip()
        if val_strip.startswith("{") and val_strip.endswith("}"):
            try:
                parsed = json.loads(val_strip)
                if isinstance(parsed, dict):
                    return clean_and_reconstruct_abstract(parsed)
            except Exception:
                pass
        return val_strip
    return str(abstract_val)

@dataclass
class Paper:
    """Standardized paper format with core fields for academic sources"""
    paper_id: str = ""         # Unique identifier (e.g., DOI, ID)
    title: str = "Sense títol" # Paper title
    authors: List[str] = field(default_factory=list)
    abstract: str = ""         # Abstract text
    doi: str = ""              # Digital Object Identifier
    published_date: Optional[str] = None   # ISO format string or year
    pdf_url: str = ""          # Direct PDF link
    url: str = ""              # URL to paper page
    source: str = ""           # Source platform
    journal: str = ""          # Journal name
    
    # Metadata and extra
    updated_date: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    citations: int = 0
    references: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        paper_id: str = "",
        title: str = "Sense títol",
        authors: List[str] = None,
        abstract: str = "",
        doi: str = "",
        published_date: Optional[str] = None,
        pdf_url: str = "",
        url: str = "",
        source: str = "",
        journal: str = "",
        updated_date: Optional[str] = None,
        categories: List[str] = None,
        keywords: List[str] = None,
        citations: int = 0,
        references: List[str] = None,
        extra: Dict[str, Any] = None,
        **kwargs
    ):
        self.paper_id = paper_id
        self.title = title
        self.authors = authors if authors is not None else []
        self.abstract = clean_and_reconstruct_abstract(abstract)
        self.doi = doi
        self.published_date = published_date
        self.pdf_url = pdf_url
        self.url = url
        self.source = source
        self.journal = journal
        self.updated_date = updated_date
        self.categories = categories if categories is not None else []
        self.keywords = keywords if keywords is not None else []
        self.citations = citations
        self.references = references if references is not None else []
        self.extra = extra if extra is not None else {}
        
        # Handle legacy year
        if "year" in kwargs:
            if not self.published_date and kwargs["year"]:
                self.published_date = str(kwargs["year"])
            self.extra["year"] = kwargs["year"]
            
        # Handle legacy citation_count
        if "citation_count" in kwargs:
            if not self.citations and kwargs["citation_count"]:
                self.citations = kwargs["citation_count"]
            self.extra["citation_count"] = kwargs["citation_count"]
            
        # Populate extra with other unknown fields
        for k, v in kwargs.items():
            if k not in ["year", "citation_count"]:
                self.extra[k] = v

    def to_dict(self) -> Dict[str, Any]:
        """Convert paper to dictionary format for serialization"""
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'doi': self.doi,
            'published_date': self.published_date,
            'pdf_url': self.pdf_url,
            'url': self.url,
            'source': self.source,
            'journal': self.journal,
            'updated_date': self.updated_date,
            'categories': self.categories,
            'keywords': self.keywords,
            'citations': self.citations,
            'references': self.references,
            'extra': self.extra
        }

