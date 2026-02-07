import logging
import asyncio
from typing import List, Annotated

from llama_index.core.workflow import Context
from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.core.llms import LLM
from llama_index.core.schema import Document
from pydantic import Field

from deep_research.config import ResearchConfig
from deep_research.services.web_search_service import WebSearchService
from deep_research.services.research_llm_service import ResearchLLMService

logger = logging.getLogger(__name__)

class ResearchTools(BaseToolSpec):
    spec_functions = [
        "optimized_query_generator",
        "web_search",
        "read_and_analyze_webpages",
        "follow_up_query_generator",
        "finalize_research",
    ]

    def __init__(self, config: ResearchConfig, llm: LLM):
        self.config = config
        self.llm = llm
        self.web_service = WebSearchService()
        self.llm_service = ResearchLLMService()

    async def optimized_query_generator(
        self, query: Annotated[str, Field(description="The initial user query.")]
    ) -> str:
        """
        Refines a research topic into an optimized query suitable for a web search engine.
        Use this at the beginning of your research.
        """
        optimized_query = await self.llm_service.generate_optimized_query(
            query, self.llm
        )
        return optimized_query

    async def web_search(
        self, ctx: Context, query: Annotated[str, Field(description="The search query.")]
    ) -> str:
        """
        Performs a web search and returns a list of 10 results. Each result includes a title, URL, and a short snippet.
        IMPORTANT: This tool does NOT access the full content of webpages. It only provides a summary.
        You must use the `read_and_analyze_webpages` tool with the URLs from the search results to access the full content.
        """
        state = await ctx.store.get_state()
        if "scratchpad" not in state:
            state["scratchpad"] = []
        if "failed_urls" not in state:
            state["failed_urls"] = []

        # Filter out previously seen URLs
        seen_urls = set(state.get("failed_urls", []))
        if "scratchpad" in state:
            for doc in state["scratchpad"]:
                if not doc.get("metadata", {}).get("error"):
                    seen_urls.add(doc.get("metadata", {}).get("source_url"))
        
        search_data, requests_made = await self.web_service.perform_search_for_agent(
            query, max_results=self.config.settings.max_search_results_per_query
        )

        if not search_data:
            return "No results found for this query."

        formatted_results = []
        for i, item in enumerate(search_data, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("desc", "") or item.get("snippet", "")
            
            marker = ""
            if url in seen_urls:
                marker = " (already seen)"
            elif url in state["failed_urls"]:
                marker = " (previously failed to load)"

            formatted_results.append(f"[{i}] Title: {title}\n    URL: {url}{marker}\n    Snippet: {snippet}")
        
        return "\n\n".join(formatted_results)

    async def _analyze_single_content(self, url: str, raw_content: str, directive: str) -> Document:
        """Helper to analyze content."""
        if "Could not read" in raw_content or "error occurred" in raw_content:
            return Document(
                text=raw_content,
                metadata={
                    "source_url": url,
                    "main_agent_directive": directive,
                    "error": True,
                    "weak_llm_analysis": raw_content,
                    "extracted_insights": []
                },
            )

        # Extract insights
        insights = await self.llm_service.extract_insights_from_content(
            content=raw_content, directive=directive, llm=self.llm
        )

        if insights:
            insights_text = "\n".join([f"- {insight['content']} (Relevance: {insight['relevance_score']})" for insight in insights])
            analysis_summary = f"Key Insights:\n{insights_text}"
        else:
            analysis_summary = "Content was read successfully, but no specific insights could be extracted."

        return Document(
            text=raw_content,
            metadata={
                "source_url": url,
                "main_agent_directive": directive,
                "weak_llm_analysis": analysis_summary,
                "extracted_insights": insights,
                "error": False
            },
        )

    async def read_and_analyze_webpages(
        self, 
        ctx: Context, 
        urls: Annotated[List[str], Field(description="List of URLs to read.")],
        directive: Annotated[str, Field(description="The goal/question to answer from these pages.")]
    ) -> str:
        """
        Reads content from a list of URLs in parallel, analyzes each for insights relevant to a directive,
        and returns a concise summary for each. Full content and analysis are saved automatically.
        Use this to efficiently process multiple sources from a web search.
        """
        max_urls = self.config.settings.max_sources
        if len(urls) > max_urls:
            logger.warning(f"Truncating URLs from {len(urls)} to {max_urls}")
            urls = urls[:max_urls]

        # Read content
        content_map = await self.web_service.read_multiple_pages_content(urls)
        
        # Analyze content in parallel
        tasks = [
            self._analyze_single_content(url, content, directive)
            for url, content in content_map.items()
        ]
        results_docs = await asyncio.gather(*tasks)

        # Update state
        async with ctx.store.edit_state() as state:
            if "scratchpad" not in state:
                state["scratchpad"] = []
            if "failed_urls" not in state:
                state["failed_urls"] = []

            for doc in results_docs:
                doc_dict = doc.to_dict()
                # Check for error
                is_error = doc.metadata.get("error", False)
                
                if is_error:
                    url = doc.metadata.get("source_url")
                    if url and url not in state["failed_urls"]:
                        state["failed_urls"].append(url)
                else:
                    state["scratchpad"].append(doc_dict)

        # Format output for the agent
        all_summaries = []
        for doc in results_docs:
            summary = doc.metadata.get("weak_llm_analysis", "No summary available.")
            url = doc.metadata.get("source_url", "unknown_url")
            all_summaries.append(f"--- Analysis for {url} ---\n{summary}")

        return "\n\n".join(all_summaries) if all_summaries else "No content could be analyzed."

    async def follow_up_query_generator(
        self, ctx: Context, original_query: Annotated[str, Field(description="The original query.")]
    ) -> str:
        """
        Based on the insights you've already collected, this tool generates new,
        specific follow-up questions to help you dig deeper into the research topic.
        """
        state = await ctx.store.get_state()
        scratchpad = state.get("scratchpad", [])
        
        insights = []
        for doc_dict in scratchpad:
            # Handle both object and dict (just in case)
            meta = doc_dict.get("metadata", {}) if isinstance(doc_dict, dict) else doc_dict.metadata
            analysis = meta.get("weak_llm_analysis", "")
            if analysis:
                insights.append(analysis)

        queries = await self.llm_service.generate_follow_up_queries(
            insights=insights, original_query=original_query, llm=self.llm
        )
        
        return "\n".join([f"- {q}" for q in queries])

    async def finalize_research(self, ctx: Context) -> str:
        """
        MUST be called as the final step. Compiles the research findings.
        """
        state = await ctx.store.get_state()
        scratchpad = state.get("scratchpad", [])
        
        # Count successful sources
        successful_count = len([
            d for d in scratchpad 
            if not (d.get("metadata", {}) if isinstance(d, dict) else d.metadata).get("error")
        ])
        
        min_sources = self.config.settings.min_sources

        if successful_count < min_sources:
            return f"Error: You have only gathered {successful_count} sources. You need at least {min_sources}. Please continue researching."

        return "Research finalized. All gathered documents are now compiled."
