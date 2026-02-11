from enum import StrEnum


class StateNamespace(StrEnum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    REPORT = "report"


class OrchestratorStateKey(StrEnum):
    RESEARCH_PLAN = "research_plan"
    CURRENT_RESEARCH = "current_research"


class ResearchStateKey(StrEnum):
    SEEN_URLS = "seen_urls"
    PENDING_EVIDENCE = "pending_evidence"
    FOLLOW_UP_QUERIES = "follow_up_queries"
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
