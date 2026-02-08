from __future__ import annotations

from enum import StrEnum


class StateNamespace(StrEnum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    REPORT = "report"


class OrchestratorStateKey(StrEnum):
    RESEARCH_NOTES = "research_notes"
    REVIEW = "review"


class ResearchStateKey(StrEnum):
    SEEN_URLS = "seen_urls"
    PENDING_EVIDENCE = "pending_evidence"
    FOLLOW_UP_QUERIES = "follow_up_queries"


class ReportStateKey(StrEnum):
    PATH = "path"
    CONTENT = "content"
    STATUS = "status"


class ReportStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
