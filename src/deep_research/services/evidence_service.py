# src/deep_research/services/evidence_service.py

import asyncio
import logging
from pathlib import PurePosixPath
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
from deep_research.services.file_service import FileService
from deep_research.services.web_search_service import WebSearchService
from deep_research.services.models import ParsedDocument
from deep_research.services.token_counting_service import TokenCountingService
from deep_research.workflows.research.searcher.models import EvidenceItem

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Orchestrates the evidence gathering pipeline:
    1. Download Content (WebSearchService)
    2. Upload Content (FileService)
    3. Parse Content (DocumentParserService)
    4. Enrich Content (ContentAnalysisService)
    """

    def __init__(
        self,
        *,
        content_analysis_service: ContentAnalysisService,
        document_parser_service: DocumentParserService,
        file_service: FileService,
        web_search_service: WebSearchService,
    ) -> None:
        self.content_analysis_service = content_analysis_service
        self.document_parser_service = document_parser_service
        self.file_service = file_service
        self.web_search_service = web_search_service

    async def generate_evidence(
        self,
        urls: List[str],
        directive: str,
        *,
        max_total_tokens: int | None = None,
        max_item_tokens: int | None = None,
        existing_total_tokens: int = 0,
    ) -> Tuple[List[EvidenceItem], List[str], bool]:
        """
        Parses and analyzes URLs to produce enriched EvidenceItems.
        Returns (items, failures, budget_exhausted).
        This service orchestrates the evidence generation process of downloading, from web, upload to LlamaIndex and parse.
        Btw, Llama parsing is insane. I don't know waht they do, but you send bytes, it eats the data and return structures.
        """

        # this is the downloading part
        download_tasks = [self.web_search_service.download_url_bytes(url) for url in urls]
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        valid_downloads: List[Tuple[str, bytes]] = []
        failures: set[str] = set()

        for url, res in zip(urls, download_results):
            if isinstance(res, BaseException) or not res:
                failures.add(url)
                logger.error(f"Failed to download {url}: {res}")
            else:
                valid_downloads.append((url, res))

        # we upload the data to llama index so we can parse by id
        # this is also good because will allow research point to actual factual data from real docs
        upload_tasks = [
            self.file_service.upload_bytes(
                content,
                filename=self._build_upload_filename(url=url),
            )
            for url, content in valid_downloads
        ]
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        files_to_parse: List[Tuple[str, str]] = [] # (file_id, url)
        
        for (url, _), res in zip(valid_downloads, upload_results):
            if isinstance(res, BaseException):
                failures.add(url)
                logger.error(f"Failed to upload {url}: {res}")
            else:
                files_to_parse.append((res, url))

        parsed_documents, parse_failures = await self.document_parser_service.parse_files(files_to_parse)
        failures.update(parse_failures)

        results = await asyncio.gather(
            *(self._process_evidence(e, directive) for e in parsed_documents)
        )

        items: List[EvidenceItem] = []
        budget_exhausted = False
        total_tokens = max(0, existing_total_tokens)

        for url, item, error in results:
            if error:
                failures.add(url)
                logger.error("Error processing evidence for %s", url, exc_info=error)
                continue

            if not item:
                continue

            # for now, we won't add per item truncation
            if max_item_tokens is not None:
                item.content = TokenCountingService.truncate_text(item.content, max_item_tokens)

            content_tokens = TokenCountingService.count_tokens(item.content)
            if max_total_tokens is not None and (total_tokens + content_tokens) > max_total_tokens:
                budget_exhausted = True
                break

            items.append(item)
            total_tokens += content_tokens

        return items, sorted(failures), budget_exhausted

    @staticmethod
    def _infer_suffix_from_url(*, url: str) -> str:
        parsed = urlparse(url)
        suffix = (PurePosixPath(parsed.path).suffix or "").lower()

        if not suffix or len(suffix) > 10 or not suffix.startswith("."):
            return ".html"

        return suffix

    @classmethod
    def _build_upload_filename(cls, *, url: str) -> str:
        suffix = cls._infer_suffix_from_url(url=url)
        return f"upload_{abs(hash(url))}{suffix}"

    async def _process_evidence(
        self, evidence: ParsedDocument, directive: str
    ) -> Tuple[str, Optional[EvidenceItem], Optional[BaseException]]:
        """
        Analyzes a single ParsedDocument item.
        Returns (url, item, error) to ensure the caller knows which URL failed.
        """
        try:
            analysis_result = await self.content_analysis_service.analyze_parsed_document(
                evidence=evidence,
                directive=directive,
            )

            if not analysis_result.insights:
                return evidence.source_url, None, None

            summary = "\n".join(
                f"- {insight.content} (Relevance: {insight.relevance_score:.2f})"
                for insight in analysis_result.insights
            )

            selected_assets = []
            for asset in evidence.assets:
                if asset.id in analysis_result.selected_asset_ids:
                    asset.is_selected = True
                    selected_assets.append(asset)

            item = EvidenceItem(
                url=evidence.source_url,
                title=evidence.metadata.get("title"),
                metadata=evidence.metadata,
                content=evidence.markdown,
                summary=summary,
                assets=selected_assets,
            )
            return evidence.source_url, item, None

        except BaseException as e:
            return evidence.source_url, None, e
