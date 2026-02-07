from __future__ import annotations

from typing import Annotated

from llama_index.core.workflow import Context
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent
from pydantic import Field

try:
    from llama_index.core.tools.tool_spec.base import BaseToolSpec
except Exception:
    from llama_index.core.tools.tool_spec import BaseToolSpec


class DemoTools(BaseToolSpec):
    """Tools for demonstrating state and HITL in FunctionAgent."""

    spec_functions = ["set_name", "get_name", "dangerous_task"]

    async def set_name(self, ctx: Context, name: str) -> str:
        """Sets the name in the context."""
        async with ctx.store.edit_state() as state:
            state["name"] = name
        return f"Name set to {name}"

    async def get_name(self, ctx: Context) -> str:
        """Gets the name from the context."""
        state = await ctx.store.get_state()
        return state.get("name", "unset")

    async def dangerous_task(self, ctx: Context) -> str:
        """A dangerous task that requires human confirmation."""
        question = "Are you sure you want to proceed?"
        
        response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=question,
            waiter_event=InputRequiredEvent(
                prefix=question,
            )
        )
        
        if response.response.strip().lower() == "yes":
            return "Dangerous task completed successfully."
        else:
            return "Dangerous task aborted."
