import logging
from datetime import date
from typing import List

from llama_index.core.prompts import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import FollowUpQueryResponse
from deep_research.services.prompts import (
    GENERATE_FOLLOW_UPS_PROMPT,
    OPTIMIZE_QUERY_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class QueryService:
    """Service for query manipulation and generation.

    Responsibilities:
    - Optimize user queries for search engines.
    - Generate follow-up questions based on context.
    """

    def __init__(self, *, llm_config: LLMModelConfig) -> None:
        self.llm = GoogleGenAI(
            model=llm_config.model,
            temperature=llm_config.temperature
        )

    async def generate_optimized_query(self, query: str) -> str:
        """
        Rewrites a user query for optimal web search results.
        Returns a simple string.
        """
        try:
            prompt_template = PromptTemplate(template=OPTIMIZE_QUERY_INSTRUCTION)
            response = await self.llm.acomplete(prompt_template.format(query=query))
            optimized_query = response.text.strip()
            logger.info(f"Optimized query '{query}' to '{optimized_query}'")
            return optimized_query
        except Exception as e:
            logger.error(f"Failed to generate optimized query for '{query}': {e}", exc_info=True)
            return query

    async def generate_follow_up_queries(self, insights: List[str], original_query: str) -> List[str]:
        """
        Generates new, targeted questions based on insights gathered so far.
        Returns a list of strings.
        """
        if not insights:
            return []
        try:
            insights_str = "\n".join([f"- {insight}" for insight in insights])
            current_date_str = date.today().isoformat()
            prompt_template = PromptTemplate(template=GENERATE_FOLLOW_UPS_PROMPT)

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
        except Exception as e:
            logger.error(f"Failed to generate follow-up queries: {e}", exc_info=True)
            return []
