from enum import StrEnum

from pydantic import BaseModel, Field

from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem


class ResearchArtifactStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OrchestratorState(BaseModel):
    research_plan: str = ""


class ResearchTurnState(BaseModel):
    seen_urls: list[str] = Field(default_factory=list)
    failed_urls: list[str] = Field(default_factory=list)
    evidence: EvidenceBundle = Field(default_factory=EvidenceBundle)
    follow_up_queries: list[str] = Field(default_factory=list)

    def clear(self) -> None:
        self.seen_urls = []
        self.failed_urls = []
        self.evidence = EvidenceBundle()
        self.follow_up_queries = []

    def add_seen_urls(self, urls: list[str]) -> None:
        merged = set(self.seen_urls)
        merged.update(map(str, urls))
        self.seen_urls = sorted(merged)

    def add_failed_urls(self, urls: list[str]) -> None:
        merged = set(self.failed_urls)
        merged.update(map(str, urls))
        self.failed_urls = sorted(merged)

    def add_evidence_items(self, items: list[EvidenceItem]) -> None:
        self.evidence.items.extend(items)


class ResearchArtifactState(BaseModel):
    path: str = "artifacts/report.md"
    content: str = ""
    draft_content: str = ""
    status: ResearchArtifactStatus = ResearchArtifactStatus.RUNNING


class DeepResearchState(BaseModel):
    orchestrator: OrchestratorState = Field(default_factory=OrchestratorState)
    research_turn: ResearchTurnState = Field(default_factory=ResearchTurnState)
    research_artifact: ResearchArtifactState = Field(default_factory=ResearchArtifactState)
