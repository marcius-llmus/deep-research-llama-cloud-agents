import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Any

from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
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
        content_map: Dict[str, str],
        directive: str
    ) -> Tuple[List[EvidenceItem], List[str]]:
        """
        Parses and analyzes raw content to produce enriched EvidenceItems.
        Returns (items, failures).
        """
        tasks = []
        urls = list(content_map.keys())

        for url in urls:
            raw_text = content_map[url]
            tasks.append(self._process_url(url, raw_text, directive))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: List[EvidenceItem] = []
        failures: List[str] = []

        for url, result in zip(urls, results):
            if isinstance(result, EvidenceItem):
                items.append(result)
            elif result is None:
                failures.append(url)
            else:
                logger.error(f"Error processing {url}: {result}")
                failures.append(url)

        return items, failures

    async def _process_url(
        self,
        url: str,
        raw_text: str,
        directive: str
    ) -> Optional[EvidenceItem]:
        """Process a single URL: parse -> enrich -> return item."""
        doc = await self.document_parser_service.parse_stub(source=url, text=raw_text)

        if not doc.text or "Could not read" in doc.text or "error occurred" in doc.text:
            logger.warning(f"Failed to parse content from {url}")
            return None

        insights = await self.content_analysis_service.extract_insights_from_content(
            content=doc.text,
            directive=directive,
        )

        if not insights:
            logger.info(f"No useful metadata extracted for {doc.source}")
            return None

        summary_lines = [f"- {insight['content']} (Relevance: {insight['relevance_score']:.2f})" for insight in insights]
        summary = "\n".join(summary_lines)

        bullets = [insight['content'] for insight in insights]

        relevance = max((insight['relevance_score'] for insight in insights), default=0.0)

        return EvidenceItem(
            url=doc.source,
            title=doc.title,
            content_type=doc.content_type,
            content=doc.text,
            summary=summary,
            topics=[], 
            bullets=bullets,
            relevance=relevance,
        )
