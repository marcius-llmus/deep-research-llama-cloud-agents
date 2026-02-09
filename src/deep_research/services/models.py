from typing import List

from pydantic import BaseModel, Field


class ExtractedInsight(BaseModel):
    """A single insight extracted from content."""
    content: str = Field(..., description="The content of the extracted insight.")
    relevance_score: float = Field(..., description="Relevance score between 0.0 and 1.0", ge=0.0, le=1.0)

class InsightExtractionResponse(BaseModel):
    """Structured response for insight extraction."""
    insights: List[ExtractedInsight] = Field(..., description="List of key insights extracted from the content.")

class FollowUpQueryResponse(BaseModel):
    """Structured response for follow-up query generation."""
    queries: List[str] = Field(..., description="List of generated follow-up queries.")


class ParsedDocument(BaseModel):
    """Normalized, cleaned document content suitable for cheap LLM enrichment.

    This is intentionally lightweight and mock-friendly.
    """

    source: str
    content_type: str  # "html" | "pdf" | "csv" | "unknown"
    text: str
    title: str | None = None
    parse_notes: str | None = None


class EvidenceEnrichmentResponse(BaseModel):
    """Structured response for cheap enrichment of an evidence source."""

    summary: str = Field(
        ..., description="Short neutral summary (3-6 sentences) of the parsed source."
    )
    topics: List[str] = Field(
        default_factory=list,
        description="3-7 short topic tags for routing/decision-making.",
    )
    bullets: List[str] = Field(
        default_factory=list,
        description="3-6 key evidence bullets relevant to the directive.",
    )
    relevance: float = Field(
        ...,
        description="Overall relevance score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
