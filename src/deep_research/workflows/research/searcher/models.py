from typing import Literal

from pydantic import BaseModel, Field
from deep_research.services.models import EvidenceAsset


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
    content_type: str | None = Field(
        default=None,
        description="Normalized content type for the evidence source (html/pdf/csv/unknown).",
    )
    summary: str | None = Field(
        default=None,
        description="Cheap-LLM summary used by orchestrator to avoid reading raw content.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Topic tags for routing/decision-making.",
    )
    content: str = Field(..., description="Full raw text content of the source.")
    bullets: list[str] = Field(default_factory=list)
    relevance: float = Field(
        0.0,
        description="Relevance score for the overall source (0.0-1.0).",
        ge=0.0,
        le=1.0,
    )
    assets: list[EvidenceAsset] = Field(default_factory=list, description="Selected rich assets (images, tables) from the source.")


class EvidenceBundle(BaseModel):
    queries: list[str] = Field(default_factory=list)
    directive: str
    items: list[EvidenceItem] = Field(default_factory=list)

    def get_summary(self) -> str:
        """Returns a concise summary of all gathered evidence."""
        if not self.items:
            return "No evidence gathered yet."
        
        lines = [f"Gathered {len(self.items)} evidence items:"]
        for i, item in enumerate(self.items, 1):
            summary = item.summary or "No summary available."
            lines.append(f"{i}. [{item.content_type or 'unknown'}] {item.url}")
            lines.append(f"   Summary: {summary}")
            lines.append(f"   Relevance: {item.relevance:.2f}")
        return "\n".join(lines)


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
