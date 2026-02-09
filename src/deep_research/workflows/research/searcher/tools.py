from __future__ import annotations

import logging
import re
from typing import Annotated

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from pydantic import Field
from workflows import Context

from deep_research.config import ResearchConfig
from deep_research.services.research_llm_service import ResearchLLMService
from deep_research.services.web_search_service import WebSearchService
from deep_research.services.document_parser_service import DocumentParserService

from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem
from deep_research.workflows.research.state_keys import (
    # ReportStateKey,
    ResearchStateKey,
    StateNamespace,
)

logger = logging.getLogger(__name__)


URL_RE = re.compile(r"https?://[^\s)\]]+")


class SearcherTools(BaseToolSpec):
    spec_functions = [
        "optimize_query",
        "follow_up_queries",
        "search_web",
        "process_sources",
        "get_gathered_evidence_summary",
    ]

    def __init__(
        self,
        *,
        config: ResearchConfig,
        web_search_service: WebSearchService | None = None,
        llm_service: ResearchLLMService | None = None,
        document_parser_service: DocumentParserService | None = None,
    ):
        self.config = config
        self.web_search_service = web_search_service or WebSearchService()
        self.llm_service = llm_service or ResearchLLMService()
        self.document_parser_service = document_parser_service or DocumentParserService()

    @staticmethod
    def _get_seen_urls(state: dict) -> set[str]:
        return set(map(str, state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS]))

    @staticmethod
    def _set_seen_urls(state: dict, seen: set[str]) -> None:
        state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS] = sorted(seen)

    async def optimize_query(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="User query to rewrite for better web search.")],
    ) -> str:
        return await self.llm_service.generate_optimized_query(query=query, llm=ctx.llm)

    async def search_web(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="Search query to run.")],
    ) -> str:
        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)

        search_data, _requests_made = await self.web_search_service.search_google(
            query=query,
            max_results=self.config.settings.max_search_results_per_query,
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
        urls: Annotated[list[str], Field(description="URLs to read.")],
        directive: Annotated[str, Field(description="What to extract and why it matters.")],
    ) -> str:
        if not urls:
            return "No URLs provided."

        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)

        candidate_urls: list[str] = []
        for url in urls:
            if url and url not in seen_urls:
                candidate_urls.append(url)

        if not candidate_urls:
            return "All provided URLs have already been processed."

        # 1) Fetch HTML content in batch; PDF/CSV parsing is mocked.
        html_urls = [u for u in candidate_urls if self.document_parser_service.classify(u) == "html"]
        html_content_map = await self.web_search_service.read_multiple_pages_content(html_urls)

        new_items: list[EvidenceItem] = []
        failures: list[str] = []

        for url in candidate_urls:
            content_type = self.document_parser_service.classify(url)
            raw_text = html_content_map.get(url, "") if content_type == "html" else None
            parsed = await self.document_parser_service.parse_stub(source=url, text=raw_text)

            parsed_text = (parsed.text or "").strip()
            if not parsed_text or "Could not read" in parsed_text or "error occurred" in parsed_text:
                failures.append(url)
                seen_urls.add(url)
                continue

            enriched = await self.llm_service.enrich_evidence(
                source=url,
                directive=directive,
                content=parsed_text,
                llm=ctx.llm,
            )

            relevance = float(enriched.get("relevance") or 0.0)
            bullets = [b for b in (enriched.get("bullets") or []) if b][:6]
            summary = (enriched.get("summary") or "").strip() or None
            topics = [t for t in (enriched.get("topics") or []) if t][:7]

            if not bullets and not summary:
                # No useful metadata; still mark as seen to avoid loops.
                seen_urls.add(url)
                continue

            new_items.append(
                EvidenceItem(
                    url=url,
                    title=None,
                    content_type=parsed.content_type,
                    summary=summary,
                    topics=topics,
                    bullets=bullets,
                    relevance=relevance,
                )
            )
            seen_urls.add(url)

        # 3) Persist to state: merge into pending evidence + update seen resources.
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

        # 4) Natural language response
        lines: list[str] = [f"Enriched {len(new_items)} new sources."]
        if new_items:
            top = sorted(new_items, key=lambda i: i.relevance, reverse=True)[:3]
            lines.append("Top sources:")
            for item in top:
                lines.append(f"- {item.url} (relevance={item.relevance:.2f}, type={item.content_type or 'unknown'})")

        if failures:
            lines.append(f"Failed to parse/read {len(failures)} sources.")
        return "\n".join(lines)

    async def get_gathered_evidence_summary(self, ctx: Context) -> str:
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

        queries = await self.llm_service.generate_follow_up_queries(
            insights=insights,
            original_query=original_query,
            llm=ctx.llm,
        )

        async with ctx.store.edit_state() as st:
            st[StateNamespace.RESEARCH][ResearchStateKey.FOLLOW_UP_QUERIES] = queries

        return "\n".join(f"- {q}" for q in queries)

 
