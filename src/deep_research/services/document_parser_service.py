import logging
import asyncio
import tempfile
import os
from typing import List, Dict
from urllib.parse import urlparse

from deep_research.services.web_search_service import WebSearchService

from deep_research.clients import get_llama_cloud_client
from deep_research.services.models import RichEvidence, EvidenceAsset

from llama_cloud.types.parsing_get_response import ParsingGetResponse

logger = logging.getLogger(__name__)


class DocumentParserService:
    """
    Uses LlamaParse v2 to parse documents (HTML, PDF, etc.) into RichEvidence.
    """

    def __init__(self, *, web_search_service: WebSearchService):
        self.client = get_llama_cloud_client()
        self.web_search_service = web_search_service

    async def upload_urls(self, urls: List[str]) -> Dict[str, str]:
        """Upload URL contents to LlamaCloud and return a url -> file_id map.

        This is intentionally separate from parsing so we can:
        - reuse uploaded file ids later
        - decouple network scraping from parsing costs
        """
        if not urls:
            return {}

        tasks = [self._upload_single_binary(url=url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        file_ids_by_url: Dict[str, str] = {}

        for url, res in zip(urls, results):
            if isinstance(res, Exception):
                logger.error("Failed to upload %s", url, exc_info=res)
                continue
            if res:
                file_ids_by_url[url] = res

        return file_ids_by_url

    async def parse_urls(self, urls: List[str]) -> tuple[List[RichEvidence], List[str]]:
        """Parse a list of URLs using LlamaParse v2.

        Returns a tuple of:
        - parsed RichEvidence objects
        - failed URLs (only those that truly failed upload/parse)
        """

        file_ids_by_url = await self.upload_urls(urls)

        failed_urls: set[str] = set(urls) - set(file_ids_by_url.keys())

        tasks = [self._parse_single(url=url, file_id=file_id) for url, file_id in file_ids_by_url.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results: list[RichEvidence] = []
        for url, res in zip(list(file_ids_by_url.keys()), results):
            if isinstance(res, Exception):
                failed_urls.add(url)
                logger.error("Failed to parse %s", url, exc_info=res)
                continue
            if res:
                valid_results.append(res)

        return valid_results, sorted(failed_urls)

    async def _upload_single_binary(self, *, url: str) -> str:
        """Download raw bytes and upload as-is to LlamaCloud."""

        data = await self.web_search_service.download_url_bytes(url, use_render=True, timeout=10)
        if not data:
            raise ValueError(f"Empty content downloaded for {url}")

        tmp = tempfile.NamedTemporaryFile(mode="wb", delete=False)
        try:
            tmp.write(data)
            tmp.flush()
            tmp.close()
            file_obj = await self.client.files.create(file=tmp.name, purpose="parse")
            return str(file_obj.id)
        finally:
            os.unlink(tmp.name)


    async def _parse_single(self, *, url: str, file_id: str) -> RichEvidence:
        logger.info("Parsing file_id=%s (source url=%s)", file_id, url)

        parse_kwargs = {
            "file_id": file_id,
            "tier": "cost_effective",
            "version": "latest",
            "input_options": {
                "html": {
                    "make_all_elements_visible": True,
                    "remove_navigation_elements": True,
                    "remove_fixed_elements": True,
                }
            },
            "output_options": {
                "markdown": {
                    "annotate_links": True,
                    "tables": {
                        "compact_markdown_tables": True,
                        "output_tables_as_markdown": True,
                    }
                },
                "images_to_save": ["embedded"]
            },
            "expand": [
                "markdown",
                "items",
                "images_content_metadata",
                "metadata",
            ],
        }

        job: ParsingGetResponse = await self.client.parsing.parse(**parse_kwargs)

        assets = []
        if job.images_content_metadata:
            for img in job.images_content_metadata.images:
                assets.append(EvidenceAsset(
                    id=img.filename,
                    type="image",
                    url=img.presigned_url,
                    description=f"Image extracted from {url}"
                ))

        markdown_content = ""
        if job.markdown and job.markdown.pages:
            texts = [p.markdown for p in job.markdown.pages if p.success]
            markdown_content = "\n\n".join(texts)

        if not markdown_content:
            raise ValueError(f"LlamaParse returned no markdown for {url}")

        structured_items: list[dict] = []
        if job.items and job.items.pages:
            for page in job.items.pages:
                if page.success:
                    structured_items.extend([i.model_dump() for i in page.items])

        metadata = job.metadata.model_dump() if job.metadata else {}

        return RichEvidence(
            source_url=url,
            markdown=markdown_content,
            structured_items=structured_items,
            assets=assets,
            metadata=metadata,
        )
