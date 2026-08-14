from .models import Paper
from .base import PaperSource
from .core import StealthBrowser, QueryExpander, FirecrawlClient, FulltextRetriever, FulltextFinder, UnpaywallClient
from .dialnet import DialnetSearcher
from .redined import RedinedSearcher
from .legislation import BOESearcher
from .oer import ProcomunSearcher
from .openalex import OpenAlexSearcher
from .zenodo import ZenodoSearcher
from .semantic_scholar import SemanticScholarSearcher
from .google_scholar import GoogleScholarSearcher
from .scielo import ScieloSearcher
from .spanish_uni import TeseoSearcher, GVASearcher, RodericSearcher, TDRSearcher, RiunetSearcher, RuaSearcher, UjiSearcher, RebiunSearcher
from .education import EricSearcher, EurekaSearcher, IntefSearcher
from .global_api import ArxivSearcher, CoreSearcher, PubMedSearcher, ScopusSearcher, WOSSearcher, CrossRefSearcher, EuropePMCSearcher, HALSearcher, IACRSearcher
from .latin_america import RedalycSearcher

__all__ = [
    'Paper',
    'PaperSource',
    'StealthBrowser',
    'QueryExpander',
    'FirecrawlClient',
    'FulltextRetriever',
    'FulltextFinder',
    'UnpaywallClient',
    'DialnetSearcher',
    'RedinedSearcher',
    'BOESearcher',
    'ProcomunSearcher',
    'OpenAlexSearcher',
    'ZenodoSearcher',
    'SemanticScholarSearcher',
    'GoogleScholarSearcher',
    'ScieloSearcher',
    'TeseoSearcher',
    'GVASearcher',
    'RodericSearcher',
    'TDRSearcher',
    'RiunetSearcher',
    'RuaSearcher',
    'UjiSearcher',
    'RebiunSearcher',
    'EricSearcher',
    'EurekaSearcher',
    'IntefSearcher',
    'ArxivSearcher',
    'CoreSearcher',
    'PubMedSearcher',
    'ScopusSearcher',
    'WOSSearcher',
    'RedalycSearcher',
    'CrossRefSearcher',
    'EuropePMCSearcher',
    'HALSearcher',
    'IACRSearcher'
]
