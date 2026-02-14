from typing import Literal

from pydantic import BaseModel, Field

from deep_research.workflows.text_config import TextSynthesizerConfig


class PlannerAgentOutput(BaseModel):
    """Structured output contract for the planning agent per turn."""

    decision: Literal["propose_plan", "finalize"]
    response: str = Field(description="The message to show to the user (question or plan explanation).")
    plan: str = Field(
        description=(
            "The current research plan as raw text. Always required."
        ),
    )
    text_config: TextSynthesizerConfig = Field(
        default_factory=TextSynthesizerConfig,
        description="Output configuration guidelines for downstream agents. Values are free-form strings.",
    )


class ResearchPlanState(BaseModel):
    initial_query: str | None = None
    research_id: str | None = None
    plan_text: str | None = None
    text_config: TextSynthesizerConfig = Field(default_factory=TextSynthesizerConfig)
    status: Literal["planning", "finalized", "failed"] = "planning"
