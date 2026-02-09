import logging
from datetime import date
from typing import List, Dict, Any

from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import FollowUpQueryResponse
from deep_research.services.prompts import (
    OPTIMIZE_QUERY_INSTRUCTION,
    GENERATE_FOLLOW_UPS_PROMPT,
    ENRICH_QUERY_FOR_SYNTHESIS_PROMPT,
)

logger = logging.getLogger(__name__)


class QueryService:
    """
    Service for handling query optimization, follow-up generation, and synthesis enrichment.
    """

    def __init__(self, llm_config: LLMModelConfig):
        self.llm = GoogleGenAI(
            model=llm_config.model,
            temperature=llm_config.temperature
        )

    async def generate_optimized_query(self, query: str) -> str:
        """
        Takes a user query and uses a powerful LLM to rewrite it for optimal web search results.
        """
        prompt_template = PromptTemplate(template=OPTIMIZE_QUERY_INSTRUCTION)
        response = await self.llm.acomplete(prompt_template.format(query=query))
        optimized_query = response.text.strip()
        logger.info(f"Optimized query '{query}' to '{optimized_query}'")
        return optimized_query

    async def generate_follow_up_queries(self, insights: List[str], original_query: str) -> List[str]:
        """
        Generates new, targeted questions based on insights gathered so far.
        """
        if not insights:
            return []

        prompt_template = PromptTemplate(template=GENERATE_FOLLOW_UPS_PROMPT)
        current_date_str = date.today().isoformat()
        insights_str = "\n".join([f"- {insight}" for insight in insights])

        structured_response = await self.llm.astructured_predict(
            FollowUpQueryResponse,
            prompt=prompt_template,
            original_query=original_query,
            insights=insights_str,
            current_date=current_date_str
        )

        queries = structured_response.queries
        logger.info(f"Generated {len(queries)} follow-up queries.")
        return queries

    async def enrich_query_for_synthesis(self, user_query: str, synthesizer_config: Dict[str, Any]) -> str:
        """
        Expands a user query into a detailed outline to guide the text synthesizer.
        """
        prompt_template = PromptTemplate(template=ENRICH_QUERY_FOR_SYNTHESIS_PROMPT)
        response = await self.llm.acomplete(prompt_template.format(
            user_query=user_query,
            word_count=synthesizer_config.get('word_count'),
            synthesis_type=synthesizer_config.get('synthesis_type'),
            target_audience=synthesizer_config.get('target_audience'),
            tone=synthesizer_config.get('tone'),
        ))
        return response.text.strip()
