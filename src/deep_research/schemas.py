from typing import Literal

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    clarifying_questions: list[str] = Field(default_factory=list)
    expanded_queries: list[str] = Field(default_factory=list)
    outline: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class PlannerAgentOutput(BaseModel):
    """Structured output contract for the planning agent per turn."""

    kind: Literal["question", "plan"]
    question: str | None = None
    plan: ResearchPlan | None = None


class ResearchPlanState(BaseModel):
    initial_query: str | None = None
    research_id: str | None = None
    plan: ResearchPlan = ResearchPlan()
    status: Literal["planning", "awaiting_approval", "failed"] = "planning"
    last_question: str | None = None

