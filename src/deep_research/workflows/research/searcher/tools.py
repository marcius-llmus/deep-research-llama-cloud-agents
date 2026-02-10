import logging
from typing import Annotated, List

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.core.workflow import Context
from pydantic import Field

from deep_research.config import ResearchConfig
from deep_research.services.evidence_service import EvidenceService
from deep_research.services.query_service import QueryService
from deep_research.services.web_search_service import WebSearchService
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
        "verify_research_sufficiency",
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
        query: Annotated[str, Field(description="User query to decompose into web search queries.")],
    ) -> str:
        """
        Decomposes a research topic into one or more focused web search queries.
        Use this at the beginning of your research when the prompt includes multiple asks.
        """
        decomposed = await self.query_service.generate_optimized_query(query=query)
        return decomposed.formatted or "Could not generate queries"

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
            max_results=self.config.searcher.max_results_per_query,
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
        new_items, failures = await self.evidence_service.generate_evidence(urls, directive)

        async with ctx.store.edit_state() as st:
            research_state = st[StateNamespace.RESEARCH]

            current_failed = research_state.get(ResearchStateKey.FAILED_URLS, [])
            research_state[ResearchStateKey.FAILED_URLS] = list(set(current_failed + failures))

            seen_urls = self._get_seen_urls(st)
            for item in new_items:
                seen_urls.add(item.url)
            for url in failures:
                seen_urls.add(url)
            self._set_seen_urls(st, seen_urls)

            pending_raw = research_state[ResearchStateKey.PENDING_EVIDENCE]
            pending = EvidenceBundle.model_validate(pending_raw)

            if directive:
                pending.directive = directive

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
                    cur.assets.extend(item.assets)
                else:
                    by_url[item.url] = item

            pending.items = list(by_url.values())
            research_state[ResearchStateKey.PENDING_EVIDENCE] = pending.model_dump()

        all_summaries = []
        for item in new_items:
            summary_text = item.summary or "No summary available."
            if item.bullets:
                bullets_text = "\n".join([f"- {b}" for b in item.bullets])
                summary_text += f"\n\nKey Insights:\n{bullets_text}"
            
            if item.assets:
                assets_text = "\n".join([f"- [{a.type}] {a.id}: {a.url}" for a in item.assets])
                summary_text += f"\n\nSelected Assets:\n{assets_text}"

            all_summaries.append(f"--- Analysis for {item.url} ---\n{summary_text}")

        if not all_summaries:
            return "No content could be analyzed from the provided URLs."

        return "\n\n".join(all_summaries)

    async def verify_research_sufficiency(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="The original user query to check against.")],
    ) -> str:
        """
        Checks if the gathered evidence is sufficient to answer the user's query.
        Returns an analysis of what is covered and what is missing.
        """
        state = await ctx.store.get_state()
        research_state = state[StateNamespace.RESEARCH]
        pending = research_state.get(ResearchStateKey.PENDING_EVIDENCE, {})
        items = pending.get("items", [])
        evidence_summaries = [
            f"Source: {item.get('url', 'unknown')}\n"
            f"Relevance: {item.get('relevance', 0.0)}\n"
            f"Summary: {item.get('summary', 'No summary')}"
            for item in items
        ]

        evidence_text = "\n\n".join(evidence_summaries).strip()
        if not evidence_text:
            return "No evidence gathered yet. Use web_search, then read_and_analyze_webpages to gather evidence before verifying sufficiency."

        return await self.query_service.verify_sufficiency(
            query=query,
            evidence_summaries=evidence_text
        )

    async def follow_up_query_generator(
        self,
        ctx: Context,
        original_query: Annotated[str, Field(description="Original user query.")],
    ) -> str:
        """
        Based on the insights you've already collected, this tool generates new,
        specific follow-up questions to help you dig deeper into the research topic.
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
        return "Research finalized. All gathered documents are now compiled."
