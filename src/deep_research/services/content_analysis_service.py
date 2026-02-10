import logging
from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import InsightExtractionResponse, ParsedDocument
from deep_research.services.prompts import EXTRACT_INSIGHTS_PROMPT

logger = logging.getLogger(__name__)


class ContentAnalysisService:
    """
    Service for extracting insights and analyzing content using a weaker/faster LLM.
    """

    def __init__(self, llm_config: LLMModelConfig):
        self.llm = GoogleGenAI(
            model=llm_config.model,
            temperature=llm_config.temperature
        )

    async def analyze_rich_evidence(self, evidence: ParsedDocument, directive: str) -> InsightExtractionResponse:
        """
        Uses a weak LLM to extract key insights and select relevant assets from content.
        """
        prompt_template = PromptTemplate(template=EXTRACT_INSIGHTS_PROMPT)
        
        assets_list_str = "\n".join([f"- ID: {a.id} | Type: {a.type} | URL: {a.url}" for a in evidence.assets])
        if not assets_list_str:
            assets_list_str = "(No assets found)"

        structured_response = await self.llm.astructured_predict(
            InsightExtractionResponse,
            prompt=prompt_template,
            directive=directive,
            content=evidence.markdown,
            assets_list=assets_list_str
        )

        logger.info(f"Extracted {len(structured_response.insights)} insights and selected {len(structured_response.selected_asset_ids)} assets for {evidence.source_url}")
        return structured_response
