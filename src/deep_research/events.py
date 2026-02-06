from typing import Any, Literal

from workflows.events import Event, StartEvent, StopEvent


class PlanStartEvent(StartEvent):
    """Starts a deep-research planning run."""

    initial_query: str


class PlannerTurnEvent(Event):
    """Represents a user message in the planning conversation."""

    message: str


class PlannerStatusEvent(Event):
    level: Literal["info", "warning", "error"]
    message: str


class PlannerQuestionEvent(Event):
    """Signals the UI to ask the user a question."""

    question: str


class PlannerFinalPlanEvent(Event):
    """Signals the UI that a plan is ready for review."""

    plan: dict[str, Any]


class ResearchMetadataResponse(StopEvent):
    """Metadata response used to configure the Deep Research UI at runtime."""

    research_collection: str
    research_settings_schema: dict[str, Any] | None = None


class ResearchPlanResponse(StopEvent):
    """Final response for a planning run."""

    research_id: str
    status: Literal["awaiting_approval"]
    plan: dict[str, Any]
    agent_data_id: str
