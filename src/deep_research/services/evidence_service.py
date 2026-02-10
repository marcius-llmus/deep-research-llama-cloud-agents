# src/deep_research/services/evidence_service.py

import asyncio
import logging
from typing import List, Optional, Tuple

from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
from deep_research.services.models import RichEvidence
from deep_research.services.token_counting_service import TokenCountingService
from deep_research.workflows.research.searcher.models import EvidenceItem

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Orchestrates the evidence gathering pipeline:
    1. Parse Content (DocumentParserService)
    2. Enrich Content (ContentAnalysisService)
    """

    def __init__(
        self,
        *,
        content_analysis_service: ContentAnalysisService,
        document_parser_service: DocumentParserService,
    ) -> None:
        self.content_analysis_service = content_analysis_service
        self.document_parser_service = document_parser_service

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
        """
        rich_evidences, parse_failures = await self.document_parser_service.parse_urls(urls)

        results = await asyncio.gather(
            *(self._process_evidence(e, directive) for e in rich_evidences)
        )

        items: List[EvidenceItem] = []
        failures: set[str] = set(parse_failures)
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

    async def _process_evidence(
        self, evidence: RichEvidence, directive: str
    ) -> Tuple[str, Optional[EvidenceItem], Optional[BaseException]]:
        """
        Analyzes a single RichEvidence item.
        Returns (url, item, error) to ensure the caller knows which URL failed.
        """
        try:
            analysis_result = await self.content_analysis_service.analyze_rich_evidence(
                evidence=evidence,
                directive=directive,
            )

            if not analysis_result.insights:
                return evidence.source_url, None, None

            summary = "\n".join(
                f"- {insight.content} (Relevance: {insight.relevance_score:.2f})"
                for insight in analysis_result.insights
            )
            relevance = max((i.relevance_score for i in analysis_result.insights), default=0.0)

            selected_assets = []
            for asset in evidence.assets:
                if asset.id in analysis_result.selected_asset_ids:
                    asset.is_selected = True
                    selected_assets.append(asset)

            item = EvidenceItem(
                url=evidence.source_url,
                title=evidence.metadata.get("title"),
                content=evidence.markdown,
                summary=summary,
                topics=[],
                relevance=relevance,
                assets=selected_assets,
            )
            return evidence.source_url, item, None

        except BaseException as e:
            return evidence.source_url, None, e
