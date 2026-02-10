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


class DecomposedQueryResponse(BaseModel):
    """Structured response for decomposing a user request into web search queries."""

    queries: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description=(
            "Decomposed web search queries. Output 1 query for simple requests; "
            "output multiple queries for broad or multi-part requests."
        ),
    )

    def format_queries(self, *, sep: str = "\n") -> str:
        """Join queries into a single string.

        Useful for tools / agents that want a compact, human-readable list.
        """

        cleaned = [q.strip() for q in self.queries if (q or "").strip()]
        return sep.join(cleaned)

    @property
    def formatted(self) -> str:
        """Convenience accessor for newline-joined queries."""

        return self.format_queries(sep="\n")


class ParsedDocument(BaseModel):
    """Normalized, cleaned document content suitable for cheap LLM enrichment.

    This is intentionally lightweight and mock-friendly.
    """

    source: str
    content_type: str  # "html" | "pdf" | "csv" | "unknown"
    text: str
    title: str | None = None
    parse_notes: str | None = None
