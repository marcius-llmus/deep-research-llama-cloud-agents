import logging
import asyncio
from typing import List, Tuple, Optional

from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
from deep_research.workflows.research.searcher.models import EvidenceItem
from deep_research.services.models import RichEvidence

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
        directive: str
    ) -> Tuple[List[EvidenceItem], List[str]]:
        """
        Parses and analyzes URLs to produce enriched EvidenceItems.
        Returns (items, failures).
        """
        rich_evidences = await self.document_parser_service.parse_urls(urls)

        tasks = [self._process_evidence(evidence, directive) for evidence in rich_evidences]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: List[EvidenceItem] = []
        failures: set[str] = set(urls)

        for result in results:
            if isinstance(result, EvidenceItem):
                items.append(result)
                failures.discard(result.url)
            elif result is None:
                continue
            elif isinstance(result, Exception):
                logger.error("Error processing evidence", exc_info=result)

        return items, sorted(failures)

    async def _process_evidence(
        self,
        evidence: RichEvidence,
        directive: str
    ) -> Optional[EvidenceItem]:
        """Process a single RichEvidence: analyze -> return item."""

        markdown = (evidence.markdown or "").strip()
        if not markdown:
            return None

        analysis_result = await self.content_analysis_service.analyze_rich_evidence(
            evidence=RichEvidence(
                source_url=evidence.source_url,
                content_type=evidence.content_type,
                markdown=markdown,
                structured_items=evidence.structured_items,
                assets=evidence.assets,
                metadata=evidence.metadata,
            ),
            directive=directive,
        )

        if not analysis_result.insights:
            return None

        summary_lines = [f"- {insight.content} (Relevance: {insight.relevance_score:.2f})" for insight in analysis_result.insights]
        summary = "\n".join(summary_lines)

        bullets = [insight.content for insight in analysis_result.insights]

        relevance = max((insight.relevance_score for insight in analysis_result.insights), default=0.0)

        selected_assets = []
        for asset in evidence.assets:
            if asset.id in analysis_result.selected_asset_ids:
                asset.is_selected = True
                selected_assets.append(asset)

        return EvidenceItem(
            url=evidence.source_url,
            title=evidence.metadata.get("title"),
            content_type=evidence.content_type,
            content=evidence.markdown,
            summary=summary,
            topics=[],
            bullets=bullets,
            relevance=relevance,
            assets=selected_assets
        )
