from enum import StrEnum
from contextlib import asynccontextmanager
from typing import AsyncIterator

from pydantic import BaseModel, Field
from workflows import Context

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
    no_new_results_count: int = 0

    def clear(self) -> None:
        self.seen_urls = []
        self.failed_urls = []
        self.evidence = EvidenceBundle()
        self.follow_up_queries = []
        self.no_new_results_count = 0

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
    turn_draft: str | None = None
    status: ResearchArtifactStatus = ResearchArtifactStatus.RUNNING


class DeepResearchState(BaseModel):
    orchestrator: OrchestratorState = Field(default_factory=OrchestratorState)
    research_turn: ResearchTurnState = Field(default_factory=ResearchTurnState)
    research_artifact: ResearchArtifactState = Field(default_factory=ResearchArtifactState)


class ResearchStateAccessor:
    KEY = "deep_research_state"

    @classmethod
    async def get(cls, ctx: Context) -> DeepResearchState:
        """Read-only access to typed state."""
        data = await ctx.store.get(cls.KEY, default={})
        return DeepResearchState.model_validate(data)

    @classmethod
    @asynccontextmanager
    async def edit(cls, ctx: Context) -> AsyncIterator[DeepResearchState]:
        """Read-write access to typed state (atomic)."""
        async with ctx.store.edit_state() as store:
            raw = store.get(cls.KEY, {})
            state = DeepResearchState.model_validate(raw)
            yield state
            store[cls.KEY] = state.model_dump()
