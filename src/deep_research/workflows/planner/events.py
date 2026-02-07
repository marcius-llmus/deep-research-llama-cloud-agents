from typing import Any, Dict
from workflows.events import Event, StartEvent

from deep_research.workflows.planner.models import PlannerAgentOutput


class PlanStartEvent(StartEvent):
    """Starts a deep-research planning run."""

    initial_query: str


class PlannerTurnEvent(Event):
    """Represents a user message in the planning conversation."""

    message: str


class PlannerOutputEvent(Event):
    """Internal event carrying the planner output for a single user turn."""

    output: PlannerAgentOutput
    user_message: str
