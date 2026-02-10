import logging
from datetime import date
from typing import List

from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import LLMModelConfig
from deep_research.services.models import DecomposedQueryResponse, FollowUpQueryResponse
from deep_research.services.prompts import (
    OPTIMIZE_QUERY_INSTRUCTION,
    GENERATE_FOLLOW_UPS_PROMPT,
    VERIFY_SEARCH_SUFFICIENCY_PROMPT,
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

    async def decompose_query(self, query: str) -> DecomposedQueryResponse:
        """
        Decomposes a user request into one or more focused web search queries.
        """
        prompt_template = PromptTemplate(template=OPTIMIZE_QUERY_INSTRUCTION)
        structured_response = await self.llm.astructured_predict(
            DecomposedQueryResponse,
            prompt=prompt_template,
            query=query,
        )
        return structured_response

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

    async def verify_sufficiency(self, query: str, evidence_summaries: str) -> str:
        """
        Checks if the gathered evidence is sufficient to answer the query.
        """
        prompt_template = PromptTemplate(template=VERIFY_SEARCH_SUFFICIENCY_PROMPT)
        response = await self.llm.acomplete(prompt_template.format(
            query=query,
            evidence_summaries=evidence_summaries
        ))
        return response.text.strip()
