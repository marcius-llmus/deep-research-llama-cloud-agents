import logging
from typing import Annotated, List

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from pydantic import Field
from workflows import Context

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
        "refine_query",
        "follow_up_queries",
        "search_web",
        "process_sources",
        "get_gathered_evidence_summary",
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

    async def refine_query(
        self,
        query: Annotated[str, Field(description="User query to rewrite for better web search.")],
    ) -> str:
        return await self.query_service.generate_optimized_query(query=query)

    async def search_web(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="Search query to run.")],
    ) -> str:
        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)

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

            marker = " (already seen)" if url and url in seen_urls else ""
            formatted_results.append(
                f"[{i}] Title: {title}\n    URL: {url}{marker}\n    Snippet: {snippet}"
            )

        return "\n\n".join(formatted_results)

    async def process_sources(
        self,
        ctx: Context,
        urls: Annotated[List[str], Field(description="URLs to read.")],
        directive: Annotated[str, Field(description="What to extract and why it matters.")],
    ) -> str:
        if not urls:
            return "No URLs provided."

        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)

        candidate_urls: list[str] = []
        for url in urls:
            if not url:
                continue
            if url in seen_urls:
                continue
            candidate_urls.append(url)

        candidate_urls = candidate_urls[: self.config.searcher.max_results_per_query]

        if not candidate_urls:
            return "All provided URLs have already been processed."

        content_map = await self.web_search_service.read_multiple_pages_content(candidate_urls)
        new_items, failures = await self.evidence_service.generate_evidence(content_map, directive)
        
        for item in new_items:
            seen_urls.add(item.url)
        for url in failures:
            seen_urls.add(url)

        async with ctx.store.edit_state() as st:
            research_state = st[StateNamespace.RESEARCH]

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

        lines: list[str] = [f"Enriched {len(new_items)} new sources."]
        if new_items:
            top = sorted(new_items, key=lambda i: i.relevance, reverse=True)[:3]
            lines.append("Top sources:")
            for item in top:
                lines.append(f"- {item.url} (relevance={item.relevance:.2f}, type={item.content_type or 'unknown'})")

        if failures:
            lines.append(f"Failed to parse/read {len(failures)} sources.")
        return "\n".join(lines)

    async def get_gathered_evidence_summary(self, ctx: Context) -> str: # noqa
        state = await ctx.store.get_state()
        pending_raw = state[StateNamespace.RESEARCH][ResearchStateKey.PENDING_EVIDENCE]
        pending = EvidenceBundle.model_validate(pending_raw)
        return pending.get_summary()

    async def follow_up_queries(
        self,
        ctx: Context,
        original_query: Annotated[str, Field(description="Original user query.")],
    ) -> str:
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
