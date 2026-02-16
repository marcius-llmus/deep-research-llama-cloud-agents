import asyncio
import logging
from typing import List, Tuple

import trafilatura

from deep_research.services.models import ParsedDocument

logger = logging.getLogger(__name__)


class TrafilaturaDocumentParserService:
    """Parses downloaded HTML bytes into Markdown using Trafilatura.

    This is intentionally separate from DocumentParserService (LlamaParse) so both
    implementations can coexist and be swapped by wiring.
    """

    async def parse_files(self, files: List[Tuple[str | None, str, bytes]]) -> tuple[List[ParsedDocument], List[str]]:
        tasks = [self._parse_single(url=url, content=content) for _file_id, url, content in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[ParsedDocument] = []
        failed_urls: list[str] = []

        for (_file_id, url, _content), res in zip(files, results):
            if isinstance(res, BaseException):
                failed_urls.append(url)
                logger.error("Failed to parse url=%s (trafilatura)", url, exc_info=res)
                continue
            valid_results.append(res)

        return valid_results, sorted(failed_urls)

    async def _parse_single(self, *, url: str, content: bytes) -> ParsedDocument:
        logger.info("Parsing url=%s (trafilatura)", url)

        decoded = self._decode_bytes(content)
        extracted = trafilatura.extract(
            decoded,
            include_comments=False,
            include_tables=True,
            no_fallback=True,
        )

        markdown_content = extracted or ""
        if not markdown_content:
            logger.warning("Trafilatura returned no content for %s", url)

        return ParsedDocument(
            source_url=url,
            markdown=markdown_content,
            assets=[],
            metadata={},
        )

    @staticmethod
    def _decode_bytes(content: bytes) -> str:
        if not content:
            return ""

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace")

