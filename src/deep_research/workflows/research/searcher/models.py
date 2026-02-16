from pydantic import BaseModel, Field
from deep_research.services.models import ParsedDocumentAsset
from typing import Any


class EvidenceItem(BaseModel):
    url: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, description="Full metadata extracted from the source.")
    summary: str = Field(
        default="",
        description="Cheap-LLM summary used by orchestrator to avoid reading raw content.",
    )
    content: str = Field(default="", description="Full raw text content of the source.")
    assets: list[ParsedDocumentAsset] = Field(default_factory=list, description="Selected rich assets (images, tables) from the source.")


class EvidenceBundle(BaseModel):
    queries: list[str] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)

    def get_summary(self) -> str:
        """Returns a concise summary of all gathered evidence."""
        if not self.items:
            return "No evidence gathered yet."
        
        lines = [f"Gathered {len(self.items)} evidence items:"]
        for i, item in enumerate(self.items, 1):
            lines.append(f"{i}. [{item.title or 'Source'}]({item.url})")
            lines.append(f"   Summary: {item.summary}")
        return "\n".join(lines)

    def get_content_for_writing(self) -> str:
        """Returns the full raw content and assets for the writer."""
        if not self.items:
            return "No evidence gathered."

        sections = []
        for item in self.items:
            header = f"### Source: [{item.title or 'Untitled'}]({item.url})"

            meta_section = ""
            if item.metadata:
                meta_lines = ["**Metadata:**"]
                for k, v in item.metadata.items():
                    if k == "pages":
                        continue
                    meta_lines.append(f"- {k}: {v}")
                meta_section = "\n".join(meta_lines)

            assets_section = ""
            if item.assets:
                assets_lines = ["**Relevant Assets:**"]
                for asset in item.assets:
                    desc = asset.description or "Asset"
                    if asset.type == "image":
                        assets_lines.append(f"![{desc}]({asset.url})")
                    else:
                        assets_lines.append(f"- [{asset.type}] {desc} ({asset.url})")
                assets_section = "\n".join(assets_lines)

            content_section = item.content or "(No raw content available)"

            parts = [header]
            if meta_section:
                parts.append(meta_section)
            if assets_section:
                parts.append(assets_section)
            parts.append(content_section)

            sections.append("\n\n".join(parts))

        return "\n\n---\n\n".join(sections)
