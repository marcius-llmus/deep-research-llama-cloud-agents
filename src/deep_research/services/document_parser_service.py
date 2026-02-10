import logging
import asyncio
import tempfile
from typing import List, Dict, Tuple
from urllib.parse import urlparse

from deep_research.services.web_search_service import WebSearchService

from deep_research.clients import get_llama_cloud_client
from deep_research.services.models import RichEvidence, EvidenceAsset
from llama_cloud.types.parsing_create_params import (
    InputOptions,
    InputOptionsHTML,
    OutputOptions,
    OutputOptionsMarkdown,
    OutputOptionsMarkdownTables,
)

logger = logging.getLogger(__name__)


class DocumentParserService:
    """
    Uses LlamaParse v2 to parse documents (HTML, PDF, etc.) into RichEvidence.
    """

    def __init__(self, *, web_search_service: WebSearchService):
        self.client = get_llama_cloud_client()
        self.web_search_service = web_search_service

    @staticmethod
    def _guess_suffix_and_kind(*, url: str) -> Tuple[str, str]:
        """Best-effort guess of file suffix and high-level kind.

        Kind is used to decide whether to pass HTML input options to LlamaParse.
        """

        path = (urlparse(url).path or "").lower()

        if path.endswith(".pdf"):
            return ".pdf", "pdf"
        if path.endswith(".csv"):
            return ".csv", "csv"
        if path.endswith(".tsv"):
            return ".tsv", "csv"
        if path.endswith(".xlsx"):
            return ".xlsx", "spreadsheet"
        if path.endswith(".xls"):
            return ".xls", "spreadsheet"

        if path.endswith(".png"):
            return ".png", "image"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return ".jpg", "image"
        if path.endswith(".svg"):
            return ".svg", "image"
        if path.endswith(".webp"):
            return ".webp", "image"
        if path.endswith(".gif"):
            return ".gif", "image"

        return ".bin", "binary"

    async def upload_urls(self, urls: List[str]) -> Dict[str, str]:
        """Upload URL contents to LlamaCloud and return a url -> file_id map.

        This is intentionally separate from parsing so we can:
        - reuse uploaded file ids later
        - decouple network scraping from parsing costs
        """
        if not urls:
            return {}

        text_by_url = await self.web_search_service.read_multiple_pages_content(urls)

        tasks = []
        for url in urls:
            if url in text_by_url and (text_by_url[url] or "").strip():
                tasks.append(self._upload_single_text(url=url, content=text_by_url[url]))
            else:
                tasks.append(self._upload_single_binary(url=url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        file_ids_by_url: Dict[str, str] = {}

        for url, res in zip(urls, results):
            if isinstance(res, Exception):
                logger.error("Failed to upload %s", url, exc_info=res)
                continue
            if res:
                file_ids_by_url[url] = res

        return file_ids_by_url

    async def parse_urls(self, urls: List[str]) -> List[RichEvidence]:
        """
        Parses a list of URLs using LlamaParse v2.
        """
        file_ids_by_url = await self.upload_urls(urls)
        tasks = [self._parse_single(url=url, file_id=file_id) for url, file_id in file_ids_by_url.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for url, res in zip(list(file_ids_by_url.keys()), results):
            if isinstance(res, Exception):
                logger.error(f"Failed to parse {url}: {res}")
            elif res:
                valid_results.append(res)
        
        return valid_results

    async def _upload_single_text(self, *, url: str, content: str) -> str:
        """Upload already-downloaded text content as an HTML-ish file."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=True, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            file_obj = await self.client.files.create(file=f.name, purpose="parse")
        return str(file_obj.id)

    async def _upload_single_binary(self, *, url: str) -> str:
        """Download raw bytes and upload as-is to LlamaCloud."""

        data = await self.web_search_service.download_url_bytes(url)

        suffix, _kind = self._guess_suffix_and_kind(url=url)

        tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)
        try:
            tmp.write(data)
            tmp.flush()
            tmp.close()
            file_obj = await self.client.files.create(file=tmp.name, purpose="parse")
            return str(file_obj.id)
        finally:
            try:
                import os

                os.unlink(tmp.name)
            except Exception:
                logger.warning("Failed to delete temp file %s", tmp.name, exc_info=True)

    async def _parse_single(self, *, url: str, file_id: str) -> RichEvidence:
        logger.info("Parsing file_id=%s (source url=%s)", file_id, url)

        _suffix, kind = self._guess_suffix_and_kind(url=url)

        input_options: InputOptions | None = None
        if kind == "html":
            html_options: InputOptionsHTML = {
                "remove_navigation_elements": True,
                "remove_fixed_elements": True,
                "make_all_elements_visible": True,
            }
            input_options = {"html": html_options}

        markdown_tables_options: OutputOptionsMarkdownTables = {
            "output_tables_as_markdown": True,
        }
        markdown_options: OutputOptionsMarkdown = {
            "annotate_links": True,
            "tables": markdown_tables_options,
        }
        output_options: OutputOptions = {"images_to_save": ["embedded"], "markdown": markdown_options}

        parse_kwargs = {
            "file_id": file_id,
            "tier": "cost_effective",
            "version": "latest",
            "output_options": output_options,
            "expand": [
                "markdown_full",
                "items",
                "images_content_metadata",
                "metadata",
            ],
        }
        if input_options is not None:
            parse_kwargs["input_options"] = input_options

        job = await self.client.parsing.parse(**parse_kwargs)

        assets = []
        if job.images_content_metadata:
            for img in job.images_content_metadata.images:
                assets.append(EvidenceAsset(
                    id=img.filename,
                    type="image",
                    url=img.presigned_url,
                    description=f"Image extracted from {url}"
                ))

        if not job.markdown_full:
            raise ValueError(f"LlamaParse returned no markdown_full for {url}")

        return RichEvidence(
            source_url=url,
            content_type="unknown",
            markdown=job.markdown_full,
            structured_items=job.items or [],
            assets=assets,
            metadata=job.metadata or {}
        )
