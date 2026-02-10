from pydantic import BaseModel, Field
from deep_research.services.models import EvidenceAsset


class EvidenceItem(BaseModel):
    url: str
    title: str | None = None
    summary: str = Field(
        default="",
        description="Cheap-LLM summary used by orchestrator to avoid reading raw content.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Topic tags for routing/decision-making.",
    )
    content: str = Field(default="", description="Full raw text content of the source.")
    relevance: float = Field(
        0.0,
        description="Relevance score for the overall source (0.0-1.0).",
        ge=0.0,
        le=1.0,
    )
    assets: list[EvidenceAsset] = Field(default_factory=list, description="Selected rich assets (images, tables) from the source.")


class EvidenceBundle(BaseModel):
    queries: list[str] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)

    def get_summary(self) -> str:
        """Returns a concise summary of all gathered evidence."""
        if not self.items:
            return "No evidence gathered yet."
        
        lines = [f"Gathered {len(self.items)} evidence items:"]
        for i, item in enumerate(self.items, 1):
            lines.append(f"{i}. {item.url}")
            lines.append(f"   Summary: {item.summary}")
            lines.append(f"   Relevance: {item.relevance:.2f}")
        return "\n".join(lines)
