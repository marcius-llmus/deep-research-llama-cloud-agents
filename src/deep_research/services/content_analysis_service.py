import logging
from typing import List, Dict, Any

from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import InsightExtractionResponse
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

    async def extract_insights_from_content(self, content: str, directive: str) -> List[Dict[str, Any]]:
        """
        Uses a weak LLM to extract key insights from content based on a directive.
        """
        prompt_template = PromptTemplate(template=EXTRACT_INSIGHTS_PROMPT)
        structured_response = await self.llm.astructured_predict(
            InsightExtractionResponse,
            prompt=prompt_template,
            directive=directive,
            content=content
        )

        insights = [insight.model_dump() for insight in structured_response.insights]
        logger.info(f"Extracted {len(insights)} insights for directive: '{directive[:50]}...'")
        return insights
