from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SearchTurnPlan(BaseModel):
    """Structured output for the search planner step.

    This is produced by the orchestrator agent and drives a single
    search->read->extract cycle.
    """

    queries: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Search queries to run next (keep short, focus on high-quality sources).",
    )
    directive: str = Field(
        description="What to extract from sources and how it should change the report."
    )
    rationale: str = Field(
        description="Short explanation of why this query is necessary given the current report.",
    )


class EvidenceItem(BaseModel):
    url: str
    title: str | None = None
    bullets: list[str] = Field(default_factory=list)
    relevance: float = Field(
        0.0,
        description="Relevance score for the overall source (0.0-1.0).",
        ge=0.0,
        le=1.0,
    )


class EvidenceBundle(BaseModel):
    queries: list[str] = Field(default_factory=list)
    directive: str
    items: list[EvidenceItem] = Field(default_factory=list)


class UpdateReportResult(BaseModel):
    content: str = Field(description="Human-readable summary of the update.")
    new_report_markdown: str = Field(description="The updated report markdown.")


class ReviewDecision(BaseModel):
    decision: Literal["accept", "revise", "research_more", "finalize"]
    notes: str = Field(
        description="Reviewer feedback. If decision != accept/finalize, include specific next steps."
    )
    follow_up_queries: list[str] = Field(
        default_factory=list,
        description="If decision is research_more, suggest follow-up queries.",
    )
