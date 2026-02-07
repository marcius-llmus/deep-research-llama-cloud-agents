from __future__ import annotations

import time
from typing import Annotated

from pydantic import Field

try:
    # LlamaIndex >= 0.10
    from llama_index.core.tools.tool_spec.base import BaseToolSpec
except Exception:  # pragma: no cover
    # Fallback for older layouts.
    from llama_index.core.tools.tool_spec import BaseToolSpec  # type: ignore


class MockTools(BaseToolSpec):
    """A minimal, safe tool spec used to validate the Function Agent plumbing.

    These tools are intentionally side-effect free.
    """

    spec_functions = ["ping", "get_time", "echo"]

    async def ping(self) -> str:
        """Health-check style tool."""

        return "pong"

    async def get_time(
        self,
        *,
        unix: Annotated[
            bool,
            Field(description="If true, return unix seconds. If false, return a human-readable string."),
        ] = True,
    ) -> str:
        """Return the current time.

        This is purely a deterministic-ish utility for testing tool calls.
        """

        now = time.time()
        if unix:
            return str(int(now))
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

    async def echo(
        self,
        text: Annotated[str, Field(description="Text to echo back.")],
    ) -> str:
        """Echo input back."""

        return text

