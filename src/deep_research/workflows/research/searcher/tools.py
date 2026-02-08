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
from deep_research.services.file_service import read_text_file

from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem
from deep_research.workflows.research.state_keys import (
    ReportStateKey,
    ResearchStateKey,
    StateNamespace,
)

logger = logging.getLogger(__name__)


URL_RE = re.compile(r"https?://[^\s)\]]+")


class SearcherTools(BaseToolSpec):
    spec_functions = [
        "optimize_query",
        "get_report",
        "search_web",
        "read_and_extract_evidence",
        "update_pending_evidence",
        "follow_up_queries",
    ]

    def __init__(
        self,
        *,
        config: ResearchConfig,
        web_search_service: WebSearchService | None = None,
        llm_service: ResearchLLMService | None = None,
    ):
        self.config = config
        self.web_search_service = web_search_service or WebSearchService()
        self.llm_service = llm_service or ResearchLLMService()

    @staticmethod
    def _get_report_path(state: dict) -> str:
        return state[StateNamespace.REPORT][ReportStateKey.PATH]

    @staticmethod
    def _get_seen_urls(state: dict) -> set[str]:
        return set(map(str, state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS]))

    @staticmethod
    def _set_seen_urls(state: dict, seen: set[str]) -> None:
        state[StateNamespace.RESEARCH][ResearchStateKey.SEEN_URLS] = sorted(seen)

    @classmethod
    def _extract_urls_from_text(cls, text: str) -> set[str]:
        return set(URL_RE.findall(text))

    async def get_report(self, ctx: Context) -> str:
        state = await ctx.store.get_state()
        report_path = self._get_report_path(state)
        return read_text_file(report_path)

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
        report_path = self._get_report_path(state)
        report_text = read_text_file(report_path)
        seen_urls |= self._extract_urls_from_text(report_text)

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

    async def read_and_extract_evidence(
        self,
        ctx: Context,
        urls: Annotated[list[str], Field(description="URLs to read.")],
        directive: Annotated[str, Field(description="What to extract from these pages.")],
    ) -> str:
        if not urls:
            return EvidenceBundle(queries=[], directive=directive, items=[]).model_dump_json()

        state = await ctx.store.get_state()
        seen_urls = self._get_seen_urls(state)
        report_path = self._get_report_path(state)

        report_text = read_text_file(report_path)
        seen_urls |= self._extract_urls_from_text(report_text)

        candidate_urls: list[str] = []
        for url in urls:
            if url and url not in seen_urls:
                candidate_urls.append(url)

        if not candidate_urls:
            return EvidenceBundle(queries=[], directive=directive, items=[]).model_dump_json()

        max_urls = min(len(candidate_urls), 5)
        candidate_urls = candidate_urls[:max_urls]

        content_map = await self.web_search_service.read_multiple_pages_content(candidate_urls)

        items: list[EvidenceItem] = []
        for url, raw_content in content_map.items():
            if not raw_content or "Could not read" in raw_content or "error occurred" in raw_content:
                seen_urls.add(url)
                continue

            insights = await self.llm_service.extract_insights_from_content(
                content=raw_content,
                directive=directive,
                llm=ctx.llm,
            )

            # Keep only useful bullets
            good = [i for i in insights if float(i.get("relevance_score", 0.0)) >= 0.65]
            bullets = [i["content"] for i in good if i.get("content")][:5]
            if not bullets:
                seen_urls.add(url)
                continue

            relevance = max(float(i.get("relevance_score", 0.0)) for i in good) if good else 0.0
            items.append(
                EvidenceItem(url=url, bullets=bullets, relevance=relevance)
            )
            seen_urls.add(url)

        async with ctx.store.edit_state() as st:
            self._set_seen_urls(st, seen_urls)

        bundle = EvidenceBundle(queries=[], directive=directive, items=items)
        return bundle.model_dump_json()

    async def update_pending_evidence(
        self,
        ctx: Context,
        evidence_bundle_json: Annotated[str, Field(description="EvidenceBundle JSON to merge into pending evidence.")],
    ) -> str:
        try:
            incoming = EvidenceBundle.model_validate_json(evidence_bundle_json)
        except Exception as e:
            raise ValueError(f"Invalid evidence bundle JSON: {e}") from e

        async with ctx.store.edit_state() as state:
            research_state = state[StateNamespace.RESEARCH]
            existing_raw = research_state[ResearchStateKey.PENDING_EVIDENCE]

            existing = EvidenceBundle.model_validate(existing_raw)

            by_url = {i.url: i for i in existing.items}
            for item in incoming.items:
                if item.url in by_url:
                    merged_bullets = list(dict.fromkeys(by_url[item.url].bullets + item.bullets))
                    by_url[item.url].bullets = merged_bullets
                    by_url[item.url].relevance = max(by_url[item.url].relevance, item.relevance)
                else:
                    by_url[item.url] = item
            existing.items = list(by_url.values())
            existing.directive = incoming.directive or existing.directive
            existing.queries = list(dict.fromkeys(existing.queries + incoming.queries))

        research_state[ResearchStateKey.PENDING_EVIDENCE] = existing.model_dump()

        return "pending_evidence updated"

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

 
