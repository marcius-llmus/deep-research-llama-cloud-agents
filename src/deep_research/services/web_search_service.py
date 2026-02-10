import logging
import os
from typing import List, Dict, Any, Tuple

from llama_index.readers.oxylabs import OxylabsGoogleSearchReader
from llama_index.readers.web import OxylabsWebReader

logger = logging.getLogger(__name__)

MAX_PAGES_CAP = 2


class WebSearchService:
    """A service to encapsulate complex web search logic."""

    def __init__(self) -> None:
        self._username = os.getenv("OXYLABS_USERNAME")
        self._password = os.getenv("OXYLABS_PASSWORD")
        if not self._username or not self._password:
            raise ValueError(
                "Oxylabs credentials are required. Set OXYLABS_USERNAME and OXYLABS_PASSWORD."
            )

    async def perform_search(self, query: str, pages: int = 1) -> Any:
        """Performs a Google search and returns the raw search data object."""
        logger.info(f"Performing Google search for query: '{query}' on {pages} page(s).")
        search_reader = OxylabsGoogleSearchReader(username=self._username, password=self._password)
        return await search_reader.aget_response({'query': query, 'pages': pages, 'parse': True})

    async def search_google(self, query: str, max_results: int = 10) -> Tuple[List[Dict], int]:
        """
        Performs a Google search and returns a list of organic result dictionaries.
        Optimized for agents.
        """
        search_data = await self.perform_search(query, pages=1)
        requests_made = 1

        collected_results: List[Dict] = []
        for page in search_data.results:
            collected_results.extend(page.content['results']['organic'])

        return collected_results[:max_results], requests_made

    async def read_multiple_pages_content(self, urls: List[str]) -> Dict[str, str]:
        """
        Reads the content of multiple URLs concurrently.
        """
        if not urls:
            return {}

        reader = OxylabsWebReader(username=self._username, password=self._password)
        try:
            documents = await reader.aload_data(urls=urls)
        except Exception as e:
            logger.error("WebSearchService failed to read URLs", exc_info=e)
            return {}

        content_map: Dict[str, str] = {}
        for doc in documents:
            url = (doc.metadata or {}).get("url")
            text = (doc.text or "").strip()
            if url and text:
                content_map[url] = text

        return content_map
