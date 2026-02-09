import logging
from typing import Annotated, List

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from pydantic import Field
from llama_index.core.workflow import Context

from deep_research.config import ResearchConfig
from deep_research.services.web_search_service import WebSearchService
from deep_research.services.evidence_service import EvidenceService
from deep_research.services.query_service import QueryService

from deep_research.workflows.research.searcher.models import EvidenceBundle
from deep_research.workflows.research.state_keys import (
    ResearchStateKey,
    StateNamespace,
)

logger = logging.getLogger(__name__)


class SearcherTools(BaseToolSpec):
    spec_functions = [
        "optimized_query_generator",
        "web_search",
        "read_and_analyze_webpages",
        "follow_up_query_generator",
        "finalize_research",
    ]

    def __init__(
        self,
        *,
        config: ResearchConfig,
        web_search_service: WebSearchService,
        query_service: QueryService,
        evidence_service: EvidenceService,
    ):
        self.config = config
        self.web_search_service = web_search_service
        self.query_service = query_service
        self.evidence_service = evidence_service

    @staticmethod
    def _get_seen_urls(state: dict) -> set[str]:
        return set(map(str, state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS]))

    @staticmethod
    def _set_seen_urls(state: dict, seen: set[str]) -> None:
        state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS] = sorted(seen)

    async def optimized_query_generator(
        self,
        query: Annotated[str, Field(description="User query to rewrite for better web search.")],
    ) -> str:
        """
        Refines a research topic into an optimized query suitable for a web search engine.
        Use this at the beginning of your research.
        """
        return await self.query_service.generate_optimized_query(query=query)

    async def web_search(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="Search query to run.")],
    ) -> str:
        """
        Performs a web search and returns a list of 10 results.
        """
        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)
        failed_urls = set(state[StateNamespace.RESEARCH].get(ResearchStateKey.FAILED_URLS, []))

        search_data, _requests_made = await self.web_search_service.search_google(
            query=query,
            max_results=10,
        )
        if not search_data:
            return "No results found for this query."

        formatted_results: list[str] = []
        for i, item in enumerate(search_data, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("desc", "") or item.get("snippet", "")

            marker = ""
            if url in seen_urls:
                marker = " (already seen)"
            elif url in failed_urls:
                marker = " (previously failed to load)"

            formatted_results.append(
                f"[{i}] Title: {title}\n    URL: {url}{marker}\n    Snippet: {snippet}"
            )

        return "\n\n".join(formatted_results)

    async def read_and_analyze_webpages(
        self,
        ctx: Context,
        urls: Annotated[List[str], Field(description="URLs to read.")],
        directive: Annotated[str, Field(description="What to extract and why it matters.")],
    ) -> str:
        """
        Reads content from a list of URLs in parallel, analyzes each for insights relevant to a directive,
        and returns a concise summary for each.
        """

        max_urls = 10
        if len(urls) > max_urls:
            logger.warning(f"Truncating URLs from {len(urls)} to {max_urls}")
            urls = urls[:max_urls]

        content_map = await self.web_search_service.read_multiple_pages_content(urls)
        new_items, failures = await self.evidence_service.generate_evidence(content_map, directive)
        
        async with ctx.store.edit_state() as st:
            research_state = st[StateNamespace.RESEARCH]
            current_failed = research_state.get(ResearchStateKey.FAILED_URLS, [])
            research_state[ResearchStateKey.FAILED_URLS] = list(set(current_failed + failures))

            seen_urls = self._get_seen_urls(st)
            for item in new_items:
                seen_urls.add(item.url)
            for url in failures:
                seen_urls.add(url)

            pending_raw = research_state[ResearchStateKey.PENDING_EVIDENCE]
            pending = EvidenceBundle.model_validate(pending_raw)

            by_url = {i.url: i for i in pending.items}
            for item in new_items:
                if item.url in by_url:
                    cur = by_url[item.url]
                    cur.bullets = list(dict.fromkeys(cur.bullets + item.bullets))
                    cur.relevance = max(cur.relevance, item.relevance)
                    cur.summary = item.summary or cur.summary
                    cur.content_type = item.content_type or cur.content_type
                    if item.topics:
                        cur.topics = list(dict.fromkeys(cur.topics + item.topics))
                else:
                    by_url[item.url] = item

            pending.items = list(by_url.values())
            pending.directive = directive or pending.directive
            
            research_state[ResearchStateKey.PENDING_EVIDENCE] = pending.model_dump()
            self._set_seen_urls(st, seen_urls)

        all_summaries = []
        for item in new_items:
            summary_text = item.summary or "No summary available."
            if item.bullets:
                bullets_text = "\n".join([f"- {b}" for b in item.bullets])
                summary_text += f"\n\nKey Insights:\n{bullets_text}"
            
            all_summaries.append(f"--- Analysis for {item.url} ---\n{summary_text}")

        for failed_url in failures:
             all_summaries.append(f"--- Analysis for {failed_url} ---\nCould not read content (error or empty).")

        if not all_summaries:
            return "No content could be analyzed from the provided URLs."
        
        return "\n\n".join(all_summaries)

    async def follow_up_query_generator(
        self,
        ctx: Context,
        original_query: Annotated[str, Field(description="Original user query.")],
    ) -> str:
        """
        Based on the insights you've already collected, this tool generates new,
        specific follow-up questions.
        """
        state = await ctx.store.get_state()
        pending_raw = state[StateNamespace.RESEARCH][ResearchStateKey.PENDING_EVIDENCE]
        pending = EvidenceBundle.model_validate(pending_raw)

        insights: list[str] = []
        for item in pending.items:
            insights.extend(item.bullets)

        queries = await self.query_service.generate_follow_up_queries(
            insights=insights,
            original_query=original_query,
        )

        async with ctx.store.edit_state() as st:
            st[StateNamespace.RESEARCH][ResearchStateKey.FOLLOW_UP_QUERIES] = queries

        return "\n".join(f"- {q}" for q in queries)

    async def finalize_research(self, ctx: Context) -> str:
        """
        MUST be called as the final step.
        """
        state = await ctx.store.get_state()
        pending_raw = state[StateNamespace.RESEARCH][ResearchStateKey.PENDING_EVIDENCE]
        pending = EvidenceBundle.model_validate(pending_raw)
        
        min_sources = self.config.settings.min_sources
        successful_count = len(pending.items)
        
        if successful_count < min_sources:
            return (
                f"Error: You have not gathered enough information. "
                f"You have gathered {successful_count} sources, but must gather at least {min_sources} sources."
            )
            
        return "Research finalized. All gathered documents are now compiled."
