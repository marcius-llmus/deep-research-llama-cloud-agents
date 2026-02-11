import asyncio
import json
from typing import Any

from workflows import Context

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.state_keys import ResearchStateKey, StateNamespace


def _redact_tool_kwargs(tool_kwargs: Any) -> Any:
    if not isinstance(tool_kwargs, dict):
        return tool_kwargs
    redacted = tool_kwargs.copy()
    # Redact common large fields if they appear
    for key in ["diff", "content", "text"]:
        if key in redacted:
            val = redacted[key]
            size = len(val) if isinstance(val, str) else 0
            if size > 500:
                redacted[key] = f"<redacted {key} {size} chars>"
    return redacted


def _format_event(ev: Any) -> str | None:
    name = type(ev).__name__

    if name == "ToolCall":
        kwargs = _redact_tool_kwargs(ev.tool_kwargs)
        return f"ToolCall(name={ev.tool_name}, id={ev.tool_id}, kwargs={kwargs})"

    if name == "ToolCallResult":
        return f"ToolCallResult(name={ev.tool_name}, id={ev.tool_id}, output={ev.tool_output})"

    return None


async def _ensure_searcher_state(ctx: Context) -> None:
    """Initialize the minimal state required by SearcherTools.

    The Searcher agent assumes the orchestrator has initialized shared state.
    This helper enables running the Searcher agent standalone for debugging.
    """

    async with ctx.store.edit_state() as state:
        if StateNamespace.RESEARCH not in state:
            state[StateNamespace.RESEARCH] = {}

        research = state[StateNamespace.RESEARCH]
        research.setdefault(ResearchStateKey.SEEN_URLS, [])
        research.setdefault(ResearchStateKey.FAILED_URLS, [])
        research.setdefault(
            ResearchStateKey.PENDING_EVIDENCE,
            {
                "queries": [],
                "items": [],
            },
        )
        research.setdefault(ResearchStateKey.FOLLOW_UP_QUERIES, [])


def _print_state_snapshot(state: dict) -> None:
    research = state.get(StateNamespace.RESEARCH, {})
    seen_urls = research.get(ResearchStateKey.SEEN_URLS, [])
    pending = research.get(ResearchStateKey.PENDING_EVIDENCE, {})
    items = pending.get("items", []) if isinstance(pending, dict) else []
    follow_ups = research.get(ResearchStateKey.FOLLOW_UP_QUERIES, [])

    print("\n--- State snapshot ---")
    print(f"seen_urls: {len(seen_urls)}")
    print(f"pending_evidence.items: {len(items)}")
    print(f"follow_up_queries: {len(follow_ups)}")
    # directive was removed from pending evidence state; it is passed as a one-time tool argument.


async def main() -> None:
    ctx = Context(searcher_agent)
    await _ensure_searcher_state(ctx)

    print(
        "Searcher agent iterative runner\n\n"
        "Commands:\n"
        "  /state            - print current ctx state summary\n"
        "  /state_json        - dump full ctx state as JSON\n"
        "  /reset            - clear research state (seen_urls, evidence, follow-ups)\n"
        "  /exit             - quit\n"
    )

    while True:
        user_msg = input("👤 Query: ").strip()
        if not user_msg:
            continue

        if user_msg in {"/exit", "/quit"}:
            break

        if user_msg == "/state":
            state = await ctx.store.get_state()
            _print_state_snapshot(state)
            continue

        if user_msg == "/state_json":
            state = await ctx.store.get_state()
            print(json.dumps(state, indent=2, default=str))
            continue

        if user_msg == "/reset":
            async with ctx.store.edit_state() as state:
                state[StateNamespace.RESEARCH] = {
                    ResearchStateKey.SEEN_URLS: [],
                    ResearchStateKey.FAILED_URLS: [],
                    ResearchStateKey.PENDING_EVIDENCE: {
                        "queries": [],
                        "items": [],
                    },
                    ResearchStateKey.FOLLOW_UP_QUERIES: [],
                }
            print("Reset research state.")
            continue

        await _ensure_searcher_state(ctx)

        print("\n🤖 SearcherAgent running...")
        handler = searcher_agent.run(user_msg=user_msg, ctx=ctx)

        try:
            async for ev in handler.stream_events():
                log_msg = _format_event(ev)
                if log_msg:
                    print(f"Event: {log_msg}")
        except asyncio.CancelledError:
            print("\n(Event stream cancelled)")
            raise

        result = await handler
        print("\n🤖 Response:\n")
        print(str(result.response))

        state = await ctx.store.get_state()
        _print_state_snapshot(state)


if __name__ == "__main__":
    asyncio.run(main())
