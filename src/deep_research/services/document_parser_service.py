import logging
import asyncio
from typing import List, Tuple

from deep_research.clients import get_llama_cloud_client
from deep_research.services.models import ParsedDocument, ParsedDocumentAsset

from llama_cloud.types.parsing_get_response import ParsingGetResponse

logger = logging.getLogger(__name__)


class DocumentParserService:
    """
    Uses LlamaParse v2 to parse documents (HTML, PDF, etc.) into ParsedDocument.
    """

    def __init__(self):
        self.client = get_llama_cloud_client()

    async def parse_files(self, files: List[Tuple[str, str]]) -> tuple[List[ParsedDocument], List[str]]:
        """Parse a list of (file_id, source_url) tuples using LlamaParse v2.

        Returns a tuple of:
        - parsed ParsedDocument objects
        - failed URLs (only those that truly failed upload/parse)
        """

        tasks = [self._parse_single(url=url, file_id=file_id) for file_id, url in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results: list[ParsedDocument] = []
        failed_urls: list[str] = []

        for (file_id, url), res in zip(files, results):
            if isinstance(res, BaseException):
                failed_urls.append(url)
                logger.error("Failed to parse file_id=%s (url=%s)", file_id, url, exc_info=res)
                continue
            valid_results.append(res)

        return valid_results, sorted(failed_urls)

    async def _parse_single(self, *, url: str, file_id: str) -> ParsedDocument:
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
                "images_to_save": ["layout"]
            },
            "expand": [
                "markdown",
                "images_content_metadata",
                "metadata",
            ],
        }

        job: ParsingGetResponse = await self.client.parsing.parse(**parse_kwargs)

        assets: list[ParsedDocumentAsset] = []
        if job.images_content_metadata:
            for img in job.images_content_metadata.images:
                assets.append(
                    ParsedDocumentAsset(
                        id=img.filename,
                        type="image",
                        url=img.presigned_url,
                        description=f"Image extracted from {url}",
                    )
                )

        markdown_content = ""
        if job.markdown and job.markdown.pages:
            texts = [p.markdown for p in job.markdown.pages if p.success]
            markdown_content = "\n\n".join(texts)

        if not markdown_content:
            raise ValueError(f"LlamaParse returned no markdown for {url}")

        metadata = job.metadata.model_dump() if job.metadata else {}

        return ParsedDocument(
            source_url=url,
            markdown=markdown_content,
            assets=assets,
            metadata=metadata,
        )
