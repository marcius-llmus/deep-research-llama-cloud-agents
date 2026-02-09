import logging
import os
from typing import List, Dict

from llama_index.core.schema import Document
from llama_index.readers.oxylabs import OxylabsGoogleSearchReader
from llama_index.readers.web import OxylabsWebReader


logger = logging.getLogger(__name__)

MAX_PAGES_CAP = 2


class WebSearchService:
    """A service to encapsulate complex web search logic."""

    def __init__(self) -> None:
        username = os.getenv("OXYLABS_USERNAME")
        password = os.getenv("OXYLABS_PASSWORD")
        if not username or not password:
            raise ValueError(
                "Oxylabs credentials are required. Set OXYLABS_USERNAME and OXYLABS_PASSWORD."
            )
        self._username = username
        self._password = password

    def _get_credentials(self) -> tuple[str, str]:
        return self._username, self._password

    @staticmethod
    def extract_urls_from_search_data(search_data: List[Document]) -> List[str]:
        """Extracts unique URLs from Oxylabs search data, preserving order."""
        urls: list[str] = []
        seen: set[str] = set()
        for doc in search_data:
            url = doc.metadata.get("source_url") or doc.metadata.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    async def perform_search(
        self, query: str, pages: int = 1, *, start: int = 0
    ) -> List[Document]:
        """Performs a Google search and returns the raw search data object (Async)."""
        logger.info(f"Performing Google search for query: '{query}' on {pages} page(s).")

        reader = OxylabsGoogleSearchReader(username=self._username, password=self._password)
        search_params: dict = {
            "query": query,
            "parse": True,
        }
        if pages and pages > 1:
            search_params["pages"] = pages
        if start:
            search_params["start"] = start

        return await reader.aload_data(search_params)

    async def search_and_extract_urls(self, query: str, pages: int = 1) -> List[str]:
        """Performs a search and returns a list of unique URLs."""
        search_docs = await self.perform_search(query, pages)
        return self.extract_urls_from_search_data(search_docs)

    async def search_and_extract_urls_by_count(self, query: str, max_results: int = 10) -> List[str]:
        """
        Performs Google searches across multiple pages until reaching the target number of URLs.
        """
        collected_urls: list[str] = []
        current_page = 1

        while len(collected_urls) < max_results and current_page <= MAX_PAGES_CAP:
            try:
                search_docs = await self.perform_search(
                    query,
                    pages=1,
                    start=(current_page - 1) * 10,
                )
                page_urls = self.extract_urls_from_search_data(search_docs)

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
        return await reader.aload_data(urls=unique_urls)

    async def get_serp_content_as_text(self, query: str, pages: int = 1) -> str:
        """Performs a search and returns the SERP content as a formatted markdown string."""
        search_docs = await self.perform_search(query, pages=pages)
        context_parts = []
        
        for doc in search_docs:
            title = doc.metadata.get("title", "No Title")
            url = doc.metadata.get("source_url", doc.metadata.get("url", "No URL"))
            description = doc.text[:300] if doc.text else "No Description"
            context_parts.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n---")

        if not context_parts:
            return f"Web search for query '{query}' returned no parsable organic results."

        return "\n\n".join(context_parts)

    async def search_google(self, query: str, max_results: int = 10) -> tuple[list[dict], int]:
        """
        Performs a Google search and returns a list of organic result dictionaries.
        """
        collected_results: list[dict] = []
        current_page = 1
        requests_made = 0

        while len(collected_results) < max_results and current_page <= MAX_PAGES_CAP:
            try:
                search_docs = await self.perform_search(
                    query,
                    pages=1,
                    start=(current_page - 1) * 10,
                )
                requests_made += 1

                if not search_docs:
                    break

                for doc in search_docs:
                    url = doc.metadata.get("source_url") or doc.metadata.get("url", "")
                    if not url:
                        continue
                    collected_results.append(
                        {
                            "title": doc.metadata.get("title", "No Title"),
                            "url": url,
                            "desc": doc.text[:300] if doc.text else "",
                        }
                    )

                if len(collected_results) >= max_results:
                    break

                current_page += 1
            except Exception as e:
                logger.error(f"Error searching page {current_page} for query '{query}': {e}")
                break

        return collected_results[:max_results], requests_made

    async def read_multiple_pages_content(self, urls: List[str]) -> Dict[str, str]:
        """
        Reads the content of multiple URLs concurrently.
        Returns a dictionary mapping URL to its content or a descriptive error message on failure.
        """
        if not urls:
            return {}

        reader = OxylabsWebReader(username=self._username, password=self._password)
        
        try:
            documents = await reader.aload_data(urls=urls)
            
            content_map = {doc.metadata.get('source_url', doc.metadata.get('url', 'unknown')): doc.text for doc in documents}

            for url in urls:
                if url not in content_map:
                    content_map[url] = f"Could not read any content from the URL: {url}"

            return content_map
        except Exception as e:
            logger.error(f"WebSearchService failed to read URLs: {e}", exc_info=True)
            return {url: f"An error occurred while trying to read the URL {url}: {str(e)}" for url in urls}
