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
    CURRENT_QUERY = "current_query"
    FAILED_URLS = "failed_urls"


class ReportStateKey(StrEnum):
    PATH = "path"
    CONTENT = "content"
    DRAFT_CONTENT = "draft_content"
    STATUS = "status"


class ReportStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
