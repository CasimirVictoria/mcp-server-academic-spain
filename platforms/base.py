from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Paper

class PaperSource(ABC):
    """Abstract base class for academic paper sources."""

    @abstractmethod
    async def search(self, query: str, limit: int = 10, **kwargs) -> List[Paper]:
        """Search papers matching the query.

        Args:
            query: Search query string.
            limit: Maximum results to return.
            **kwargs: Source-specific parameters.

        Returns:
            List of Paper objects.
        """

    async def download_pdf(self, paper_id: str, save_path: str) -> Optional[str]:
        """Download the PDF for a given paper.

        Args:
            paper_id: Platform-specific paper identifier.
            save_path: Directory to save the downloaded PDF.

        Returns:
            Path to the saved PDF file or None if failed.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support PDF downloads."
        )
