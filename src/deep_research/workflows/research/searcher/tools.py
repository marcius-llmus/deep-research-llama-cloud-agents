import logging
from typing import Annotated, List

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from workflows import Context
from pydantic import Field

from deep_research.config import ResearchConfig
from deep_research.services.evidence_service import EvidenceService
from deep_research.services.query_service import QueryService
from deep_research.services.web_search_service import WebSearchService
from deep_research.services.token_counting_service import TokenCountingService
from deep_research.workflows.research.state import ResearchStateAccessor

logger = logging.getLogger(__name__)


class SearcherTools(BaseToolSpec):
    spec_functions = [
        "decompose_query",
        "web_search",
        "generate_evidences",
        "verify_research_sufficiency",
        "follow_up_query_generator",
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


    async def decompose_query(
        self,
        query: Annotated[str, Field(description="User query to decompose into web search queries.")],
    ) -> str:
        """
        Decomposes a research topic into one or more focused web search queries.
        Use this at the beginning of your research when the prompt includes multiple asks.
        """
        decomposed = await self.query_service.decompose_query(query=query)
        return decomposed.formatted or "Could not generate queries"

    async def web_search(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="Search query to run.")],
    ) -> str:
        """
        Performs a web search and returns a list of 10 results.
        """
        state = await ResearchStateAccessor.get(ctx)
        seen_urls = set(map(str, state.research_turn.seen_urls))
        failed_urls = set(map(str, state.research_turn.failed_urls))

        search_data, _requests_made = await self.web_search_service.search_google(
            query=query,
            max_results=self.config.searcher.max_results_per_query,
        )
        if not search_data:
            return "No results found for this query."

        new_results: list[dict] = []
        ignored_count = 0
        for item in search_data:
            if not (url := item.get("url").strip()):
                continue
            if url in seen_urls or url in failed_urls:
                ignored_count += 1
                continue
            new_results.append(item)

        if new_results:
            async with ResearchStateAccessor.edit(ctx) as state:
                state.research_turn.add_seen_urls([r["url"] for r in new_results])

        if not new_results:
            return self._format_no_new_results_message(
                seen_urls=len(seen_urls),
                failed_urls=len(failed_urls),
            )

        return self._format_search_results(
            results=new_results,
            ignored_count=ignored_count,
        )

    @staticmethod
    def _format_no_new_results_message(*, seen_urls: int, failed_urls: int) -> str:
        return (
            "NO_NEW_RESULTS\n"
            "All results for this query are already seen/failed.\n"
            f"Seen URLs: {seen_urls} | Failed URLs: {failed_urls}\n\n"
            "You must choose one:\n"
            "1) call follow_up_query_generator(original_query=...) to generate a new angle, then web_search using one of those queries verbatim\n"
            "2) call finalize_research if evidence is already sufficient"
        )

    @staticmethod
    def _format_search_results(*, results: list[dict], ignored_count: int) -> str:
        formatted_results: list[str] = []
        for idx, item in enumerate(results, 1):
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            snippet = (item.get("desc") or item.get("snippet") or "").strip()

            formatted_results.append(
                f"[{idx}] Title: {title}\n"
                f"    URL: {url}\n"
                f"    Snippet: {snippet}"
            )

        if ignored_count:
            formatted_results.append(
                f"(Ignored {ignored_count} already seen/failed results)"
            )

        return "\n\n".join(formatted_results)

    async def generate_evidences(
        self,
        ctx: Context,
        urls: Annotated[List[str], Field(description="URLs to read.")],
        directive: Annotated[str, Field(description="What to extract and why it matters.")],
    ) -> str:
        """
        Reads content from a list of URLs in parallel, analyzes each for insights relevant to a directive,
        and returns a concise summary for each.
        """
        state = await ResearchStateAccessor.get(ctx)
        pending = state.research_turn.evidence

        existing_total_tokens = TokenCountingService.count_tokens(
            "\n\n".join([(i.content or "") for i in pending.items])
        )

        new_items, failures, budget_exhausted = await self.evidence_service.generate_evidence(
            urls,
            directive,
            max_total_tokens=self.config.settings.max_pending_evidence_tokens,
            existing_total_tokens=existing_total_tokens,
        )

        async with ResearchStateAccessor.edit(ctx) as state:
            state.research_turn.add_failed_urls(list(failures))
            state.research_turn.add_seen_urls([i.url for i in new_items] + list(failures))
            state.research_turn.add_evidence_items(new_items)

        all_summaries = []
        for item in new_items:
            summary_text = item.summary

            if item.assets:
                assets_text = "\n".join([f"- [{a.type}] {a.description or 'No desc'} (ID: {a.id}) -> {a.url}"
                        for a in item.assets])
                summary_text += f"\n\nSelected Assets:\n{assets_text}"

            all_summaries.append(f"--- Analysis for {item.url} ---\n{summary_text}")

        if not all_summaries:
            return "No content could be analyzed from the provided URLs."

        msg = "\n\n".join(all_summaries)
        if budget_exhausted:
            msg += (
                "\n\n[NOTE] Reached the configured max pending evidence token budget for this turn. "
                "Additional sources were not added."
            )
        return msg

    async def verify_research_sufficiency(
        self,
        ctx: Context,
        query: Annotated[str, Field(description="The original user query to check against.")],
    ) -> str:
        """
        Checks if the gathered evidence is sufficient to answer the user's query.
        Returns an analysis of what is covered and what is missing.
        """
        state = await ResearchStateAccessor.get(ctx)
        evidence_summaries = [
            f"Source: {item.url}\nSummary: {item.summary}"
            for item in state.research_turn.evidence.items
        ]

        evidence_text = "\n\n".join(evidence_summaries).strip()
        if not evidence_text:
            return "No evidence gathered yet. Use web_search, then generate_evidences to gather evidence before verifying sufficiency."

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
        state = await ResearchStateAccessor.get(ctx)
        pending = state.research_turn.evidence

        insights: list[str] = []
        for item in pending.items:
            insights.append(item.summary)

        queries = await self.query_service.generate_follow_up_queries(
            insights=insights,
            original_query=original_query,
        )

        async with ResearchStateAccessor.edit(ctx) as state:
            state.research_turn.follow_up_queries = queries

        return "\n".join(f"- {q}" for q in queries)

    # in order to return direct, it doesn't go in spec_functions
    @staticmethod
    async def finalize_research(ctx: Context) -> str:
        state = await ResearchStateAccessor.get(ctx)
        items = state.research_turn.evidence.items

        total_items = len(items)
        seen_urls = len(state.research_turn.seen_urls)
        failed_urls = len(state.research_turn.failed_urls)
        follow_up_queries = len(state.research_turn.follow_up_queries)

        image_assets = 0
        other_assets = 0
        for item in items:
            for asset in item.assets:
                if asset.type == "image":
                    image_assets += 1
                else:
                    other_assets += 1

        return (
            "Searcher agent has finished collecting evidences.\n\n"
            "Evidence\n"
            f"- Total items: {total_items}\n"
            f"- Seen URLs: {seen_urls}\n"
            f"- Failed URLs: {failed_urls}\n"
            f"- Follow-up queries: {follow_up_queries}\n\n"
            "Assets\n"
            f"- Images selected: {image_assets}\n"
            f"- Other assets selected: {other_assets}\n"
        )
