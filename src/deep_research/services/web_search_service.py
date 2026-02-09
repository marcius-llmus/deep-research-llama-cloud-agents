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

        try:
            reader = OxylabsWebReader(username=self._username, password=self._password)
            documents = await reader.aload_data(urls=urls)

            content_map = {doc.metadata['url']: doc.text for doc in documents if 'url' in doc.metadata}

            # For URLs that failed
            for url in urls:
                if url not in content_map:
                    content_map[url] = f"Could not read any content from the URL: {url}"

            return content_map
        except Exception as e:
            logger.error(f"WebSearchService failed to read URLs: {e}", exc_info=True)
            return {url: f"An error occurred while trying to read the URL {url}: {str(e)}" for url in urls}
