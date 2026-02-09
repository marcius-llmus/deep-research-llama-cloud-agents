import logging
from typing import List, Dict, Tuple

from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
from deep_research.workflows.research.searcher.models import EvidenceItem

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Orchestrates the evidence gathering pipeline:
    1. Fetch Content (WebSearchService)
    2. Parse Content (DocumentParserService)
    3. Enrich Content (ContentAnalysisService)
    4. Construct EvidenceItem (EvidenceService)
    """

    def __init__(
        self,
        *,
        analysis_service: ContentAnalysisService,
        document_parser_service: DocumentParserService,
    ) -> None:
        self.analysis_service = analysis_service
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
        items: List[EvidenceItem] = []
        failures: List[str] = []

        for url, raw_text in content_map.items():
            doc = await self.document_parser_service.parse_stub(source=url, text=raw_text)
            
            if not doc.text or "Could not read" in doc.text or "error occurred" in doc.text:
                logger.warning(f"Failed to parse content from {url}")
                failures.append(url)
                continue

            enriched = await self.analysis_service.summarize(
                source=doc.source,
                directive=directive,
                content=doc.text,
            )

            relevance = enriched.relevance
            bullets = enriched.bullets[:6]
            summary = enriched.summary or None
            topics = enriched.topics[:7]

            if not bullets and not summary:
                logger.info(f"No useful metadata extracted for {doc.source}")
                continue

            items.append(
                EvidenceItem(
                    url=doc.source,
                    title=None,
                    content_type=doc.content_type,
                    content=doc.text,
                    summary=summary,
                    topics=topics,
                    bullets=bullets,
                    relevance=relevance,
                )
            )

        return items, failures
