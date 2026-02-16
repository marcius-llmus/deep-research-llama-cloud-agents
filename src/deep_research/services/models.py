from typing import List, Literal, Any

from pydantic import BaseModel, Field


class ParsedDocumentAsset(BaseModel):
    id: str = Field(..., description="Unique ID or filename of the asset")
    type: Literal["image", "unknown"] = "unknown"
    url: str = Field(..., description="Presigned URL or source URL")
    description: str | None = None
    is_selected: bool = False


class ParsedDocument(BaseModel):
    """A parsed document snapshot normalized from the upstream parser response."""

    source_url: str
    markdown: str
    assets: List[ParsedDocumentAsset] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedInsight(BaseModel):
    """A single insight extracted from content."""
    content: str = Field(..., description="The content of the extracted insight.")
    relevance_score: float = Field(..., description="Relevance score between 0.0 and 1.0", ge=0.0, le=1.0)
    topic_density_score: float = Field(..., description="A score (0.0 to 1.0) indicating how much of the source text is dedicated to this specific insight/topic. High density means the source goes deep into this topic.", ge=0.0, le=1.0)


class InsightExtractionResponse(BaseModel):
    """Structured response for insight extraction."""
    insights: List[ExtractedInsight] = Field(..., description="List of key insights extracted from the content.")
    selected_asset_ids: List[str] = Field(default_factory=list, description="List of asset IDs that are relevant to the directive.")


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
