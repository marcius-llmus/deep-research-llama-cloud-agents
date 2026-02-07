"""Deep research configuration.

Configuration is loaded from configs/config.json via Workflows ResourceConfig.

This project intentionally focuses on Deep Research planning/execution only.
"""

from typing import Literal

from pydantic import BaseModel


RESEARCH_SESSIONS_COLLECTION: str = "research-sessions"


class ResearchCollections(BaseModel):
    """Agent Data collections used by the Deep Research experience."""

    research_collection: str = RESEARCH_SESSIONS_COLLECTION


class ResearchSettings(BaseModel):
    """Runtime settings for deep research planning/execution."""

    max_report_update_size: int = 800
    max_search_results_per_query: int = 5
    min_sources: int = 2
    max_sources: int = 20
    timeout_seconds: int = 600


class LLMConfig(BaseModel):
    """LLM configuration for the planner agent.

    This is intentionally minimal; the concrete provider/model mapping
    can be extended as we iterate.
    """

    provider: Literal["openai"] = "openai"
    model: str = "gpt-5"
    temperature: float = 0.2
    reasoning_effort: Literal["low", "medium", "high"] = "low"


class ResearchConfig(BaseModel):
    """Deep research configuration loaded from configs/config.json (path: research)."""

    llm: LLMConfig = LLMConfig()
    collections: ResearchCollections = ResearchCollections()
    settings: ResearchSettings = ResearchSettings()
