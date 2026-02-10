import logging
import os
from typing import Dict, List, Tuple

import asyncio
import base64
import json

import requests
from llama_index.readers.oxylabs import OxylabsGoogleSearchReader
from llama_index.readers.web import OxylabsWebReader

logger = logging.getLogger(__name__)


class WebSearchService:
    """A service to encapsulate complex web search logic."""

    def __init__(self) -> None:
        self._username = os.getenv("OXYLABS_USERNAME")
        self._password = os.getenv("OXYLABS_PASSWORD")
        if not self._username or not self._password:
            raise ValueError(
                "Oxylabs credentials are required. Set OXYLABS_USERNAME and OXYLABS_PASSWORD."
            )

    async def search_google(self, query: str, max_results: int = 10) -> Tuple[List[Dict], int]:
        """
        Performs a Google search and returns a list of organic result dictionaries.
        Optimized for agents.
        """
        _MAX_PAGES = 1
        search_reader = OxylabsGoogleSearchReader(username=self._username, password=self._password)
        search_data = await search_reader.aget_response({'query': query, 'pages': _MAX_PAGES, 'parse': True})

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
            raise ValueError("urls must not be empty")

        reader = OxylabsWebReader(username=self._username, password=self._password)
        documents = await reader.aload_data(urls=urls, additional_params={"markdown": True})

        content_map: Dict[str, str] = {}
        for doc in documents:
            url = (doc.metadata["oxylabs_job"] or {}).get("url")
            text = (doc.text or "").strip()
            if url and text:
                content_map[url] = text

        return content_map

    async def download_url_bytes(self, url: str) -> bytes:
        """Download raw bytes for a URL."""

        if not url:
            raise ValueError("url is required")

        api_url = f"https://{self._username}:{self._password}@realtime.oxylabs.io/v1/queries"
        parameters = {
            "source": "universal",
            "url": url,
            "content_encoding": "base64",
        }

        def _request() -> bytes:
            response = requests.post(api_url, json=parameters, timeout=60.0)
            if not response.ok:
                raise RuntimeError(
                    f"Oxylabs request failed: status={response.status_code} body={response.text}"
                )
            data = json.loads(response.text)
            content_base64 = data["results"][0]["content"]
            return base64.b64decode(content_base64)

        return await asyncio.to_thread(_request)
