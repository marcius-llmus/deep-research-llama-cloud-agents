from typing import Any

from workflows.events import Event, StartEvent

from deep_research.schemas import PlannerAgentOutput


class PlanStartEvent(StartEvent):
    """Starts a deep-research planning run."""

    initial_query: str


class PlannerTurnEvent(Event):
    """Represents a user message in the planning conversation."""

    message: str


class PlannerFinalPlanEvent(Event):
    """Signals the UI that a plan is ready for review."""

    plan: dict[str, Any]


class PlannerOutputEvent(Event):
    """Internal event carrying the planner output for a single user turn."""

    output: PlannerAgentOutput
    user_message: str
