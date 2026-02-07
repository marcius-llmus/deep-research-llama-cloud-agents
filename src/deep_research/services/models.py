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
