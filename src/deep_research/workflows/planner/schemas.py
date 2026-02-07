from typing import Literal

from pydantic import BaseModel, Field


class PlannerAgentOutput(BaseModel):
    """Structured output contract for the planning agent per turn."""

    decision: Literal["propose_plan", "finalize"]
    response: str = Field(description="The message to show to the user (question or plan explanation).")
    plan: str = Field(
        description="The current research plan as raw text. Always required.",
    )


class ResearchPlanState(BaseModel):
    initial_query: str | None = None
    research_id: str | None = None
    plan_text: str | None = None
    status: Literal["planning", "finalized", "failed"] = "planning"
