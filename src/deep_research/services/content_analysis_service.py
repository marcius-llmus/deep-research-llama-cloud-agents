import logging
from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import EvidenceEnrichmentResponse
from deep_research.services.prompts import ENRICH_EVIDENCE_PROMPT


logger = logging.getLogger(__name__)


class ContentAnalysisService:
    """Service for pure content analysis and enrichment.

    Responsibilities:
    - Enrich evidence with summaries, topics, and relevance scores.
    - Extract insights from content.
    """

    def __init__(self, llm_config: LLMModelConfig):
        self.llm = GoogleGenAI(
            model=llm_config.model,
            temperature=llm_config.temperature
        )

    async def summarize(
        self,
        *,
        source: str,
        directive: str,
        content: str,
        max_chars: int = 12000,
    ) -> EvidenceEnrichmentResponse:
        """Generate compact orchestrator-friendly metadata for a parsed evidence source.

        Returns a Pydantic model with: summary/topics/bullets/relevance.
        """
        try:
            trimmed = (content or "").strip()
            if max_chars and len(trimmed) > max_chars:
                trimmed = trimmed[:max_chars]

            prompt_template = PromptTemplate(template=ENRICH_EVIDENCE_PROMPT)
            return await self.llm.astructured_predict(
                EvidenceEnrichmentResponse,
                prompt=prompt_template,
                directive=directive,
                source=source,
                content=trimmed,
            )
        except Exception as e:
            logger.error(f"Failed to enrich evidence for source '{source}': {e}", exc_info=True)
            return EvidenceEnrichmentResponse(
                summary="",
                topics=[],
                bullets=[],
                relevance=0.0
            )
