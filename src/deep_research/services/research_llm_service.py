import logging
from datetime import date
from typing import Dict, List

from llama_index.core import PromptTemplate
from llama_index.core.llms import LLM

from deep_research.services.models import InsightExtractionResponse, FollowUpQueryResponse
from deep_research.services.prompts import (
    EXTRACT_INSIGHTS_PROMPT, GENERATE_FOLLOW_UPS_PROMPT, OPTIMIZE_QUERY_INSTRUCTION, ENRICH_QUERY_FOR_SYNTHESIS_PROMPT,
)

logger = logging.getLogger(__name__)


class ResearchLLMService:
    """A service for handling specialized LLM operations for deep research."""

    @classmethod
    async def generate_optimized_query(cls, query: str, llm: LLM) -> str:
        """
        Takes a user query and uses a powerful LLM to rewrite it for optimal web search results.
        """
        try:
            prompt_template = PromptTemplate(template=OPTIMIZE_QUERY_INSTRUCTION)
            response = await llm.acomplete(prompt_template.format(query=query))
            optimized_query = response.text.strip()
            logger.info(f"Optimized query '{query}' to '{optimized_query}'")
            return optimized_query
        except Exception as e:
            logger.error(f"Failed to generate optimized query for '{query}': {e}", exc_info=True)
            return query

    @classmethod
    async def extract_insights_from_content(cls, content: str, directive: str, llm: LLM) -> List[Dict]:
        """
        Uses a weak LLM to extract key insights from content based on a directive.
        """
        try:
            prompt_template = PromptTemplate(template=EXTRACT_INSIGHTS_PROMPT)
            structured_response = await llm.astructured_predict(
                InsightExtractionResponse, prompt=prompt_template, directive=directive, content=content
            )

            insights = [insight.model_dump() for insight in structured_response.parsed_output.insights] # noqa
            logger.info(f"Extracted {len(insights)} insights for directive: '{directive[:50]}...'")
            return insights
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return []

    @classmethod
    async def generate_follow_up_queries(cls, insights: List[str], original_query: str, llm: LLM) -> List[str]:
        """
        Generates new, targeted questions based on insights gathered so far.
        """
        if not insights:
            return []
        try:
            insights_str = "\n".join([f"- {insight}" for insight in insights])
            prompt_template = PromptTemplate(template=GENERATE_FOLLOW_UPS_PROMPT)
            current_date_str = date.today().isoformat()
            structured_response = await llm.astructured_predict(
                FollowUpQueryResponse, prompt=prompt_template, original_query=original_query, insights=insights_str, current_date=current_date_str
            )

            queries = structured_response.parsed_output.queries
            logger.info(f"Generated {len(queries)} follow-up queries.")
            return queries
        except Exception as e:
            logger.error(f"Failed to generate follow-up queries: {e}", exc_info=True)
            return []

    @classmethod
    async def enrich_query_for_synthesis(cls, user_query: str, synthesizer_config: Dict, llm: LLM) -> str:
        """
        Expands a user query into a detailed outline to guide the text synthesizer,
        tailoring the level of detail to the target word count and document style.
        """
        try:
            prompt_template = PromptTemplate(template=ENRICH_QUERY_FOR_SYNTHESIS_PROMPT)
            response = await llm.acomplete(prompt_template.format(
                user_query=user_query,
                word_count=synthesizer_config.get('word_count'),
                synthesis_type=synthesizer_config.get('synthesis_type'),
                target_audience=synthesizer_config.get('target_audience'),
                tone=synthesizer_config.get('tone'),
            ))

            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to enrich query '{user_query}': {e}. Falling back to original query.", exc_info=True)
            return user_query
