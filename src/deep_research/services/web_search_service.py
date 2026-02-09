import logging
import os
from typing import List, Dict, Any, Tuple

from llama_index.core.schema import Document
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

    @staticmethod
    def extract_urls_from_search_data(search_data: Any) -> List[str]:
        """Extracts unique URLs from Oxylabs search data."""
        all_urls = []
        for page_result in search_data.results:
            try:
                # page_result might be an object with .content attribute (dict)
                content = page_result.content
                if isinstance(content, dict):
                    organic_results = content.get('results', {}).get('organic', [])
                    for organic_result in organic_results:
                        url = organic_result.get('url')
                        if url:
                            all_urls.append(url)
            except (TypeError, KeyError, AttributeError):
                logger.warning("Could not parse organic results from a page in WebSearchService.")
        return all_urls

    async def perform_search(self, query: str, pages: int = 1) -> Any:
        """Performs a Google search and returns the raw search data object."""
        logger.info(f"Performing Google search for query: '{query}' on {pages} page(s).")
        search_reader = OxylabsGoogleSearchReader(username=self._username, password=self._password)
        return await search_reader.aget_response({'query': query, 'pages': pages, 'parse': True})

    async def search_and_extract_urls(self, query: str, pages: int = 1) -> List[str]:
        """Performs a search and returns a list of unique URLs."""
        search_data = await self.perform_search(query, pages)
        return self.extract_urls_from_search_data(search_data)

    async def search_and_extract_urls_by_count(self, query: str, max_results: int = 10) -> List[str]:
        """Performs Google searches across multiple pages until reaching the target number of URLs."""
        collected_urls: List[str] = []
        current_page = 1

        while len(collected_urls) < max_results and current_page <= MAX_PAGES_CAP:
            try:
                search_data = await self.perform_search(query, pages=current_page)
                page_urls = self.extract_urls_from_search_data(search_data)

                if not page_urls:
                    break

                for url in page_urls:
                    if url not in collected_urls:
                        collected_urls.append(url)

                logger.info(f"Page {current_page}: Found {len(page_urls)} URLs, total unique: {len(collected_urls)}")
                current_page += 1

            except Exception as e:
                logger.error(f"Error searching page {current_page} for query '{query}': {e}")
                break

        return collected_urls[:max_results]

    async def perform_full_search_by_count(self, query: str, max_results: int = 10) -> List[Document]:
        """Performs a search for a specific number of results and reads their content."""
        unique_urls = await self.search_and_extract_urls_by_count(query, max_results)
        if not unique_urls:
            logger.warning("WebSearchService found no URLs to read.")
            return []

        reader = OxylabsWebReader(username=self._username, password=self._password)
        documents = await reader.aload_data(urls=unique_urls)
        logger.info(f"WebSearchService read content from {len(documents)} pages for {max_results} target results.")
        return documents

    async def get_serp_content_as_text(self, query: str, pages: int = 1) -> str:
        """Performs a search and returns the SERP content as a formatted markdown string."""
        search_data = await self.perform_search(query, pages=pages)
        context_parts = []

        for page_result in search_data.results:
            try:
                content = page_result.content
                organic_results = content.get('results', {}).get('organic', [])
                for result in organic_results:
                    title = result.get('title', 'No Title')
                    description = result.get('desc', 'No Description')
                    url = result.get('url', 'No URL')
                    context_parts.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n---")
            except (AttributeError, KeyError):
                pass

        if not context_parts:
            raise ValueError(f"Web search for query '{query}' returned no parsable organic results.")

        return "\n\n".join(context_parts)

    async def search_google(self, query: str, max_results: int = 10) -> Tuple[List[Dict], int]:
        """
        Performs a Google search and returns a list of organic result dictionaries.
        Optimized for agents.
        """
        collected_results: List[Dict] = []
        current_page = 1
        requests_made = 0

        while len(collected_results) < max_results and current_page <= MAX_PAGES_CAP:
            try:
                search_data = await self.perform_search(query, pages=current_page)
                requests_made += 1
                page_results = []

                for page in search_data.results:
                    content = page.content
                    page_results.extend(content.get('results', {}).get('organic', []))

                if not page_results:
                    break

                collected_results.extend(page_results)
                current_page += 1
            except Exception as e:
                logger.error(f"Error searching page {current_page} for query '{query}': {e}")
                break

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
