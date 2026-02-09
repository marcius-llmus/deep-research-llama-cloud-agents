"""Deep research configuration.

Configuration is loaded from configs/config.json via Workflows ResourceConfig.

This project intentionally focuses on Deep Research planning/execution only.
"""
from pydantic import BaseModel, Field


class ResearchCollections(BaseModel):
    """Agent Data collections used by the Deep Research experience."""

    research_collection: str = Field(..., description="Agent Data collection name for research sessions")


class ResearchSettings(BaseModel):
    """Runtime settings for deep research planning/execution."""

    max_report_update_size: int = Field(..., ge=1)
    min_sources: int = Field(..., ge=1)
    max_sources: int = Field(..., ge=1)
    timeout_seconds: int = Field(..., ge=1)


class LLMModelConfig(BaseModel):
    """Atomic configuration for a single LLM instance."""
    model: str = Field(..., description="Google GenAI model name")
    temperature: float = Field(..., ge=0.0, le=2.0)


class PlannerConfig(BaseModel):
    main_llm: LLMModelConfig

class SearcherConfig(BaseModel):
    main_llm: LLMModelConfig
    weak_llm: LLMModelConfig

    max_results_per_query: int = Field(
        ...,
        ge=1,
        description="Maximum number of SERP results to return/process for a single search query.",
    )

class OrchestratorConfig(BaseModel):
    main_llm: LLMModelConfig

class WriterConfig(BaseModel):
    main_llm: LLMModelConfig

class ReviewerConfig(BaseModel):
    main_llm: LLMModelConfig

class ResearchConfig(BaseModel):
    """Deep research configuration loaded from configs/config.json (path: research)."""

    planner: PlannerConfig
    searcher: SearcherConfig
    orchestrator: OrchestratorConfig
    writer: WriterConfig
    reviewer: ReviewerConfig

    collections: ResearchCollections
    settings: ResearchSettings
