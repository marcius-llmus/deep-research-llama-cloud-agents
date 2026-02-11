import asyncio
import json
from typing import Any

from workflows import Context

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.state_keys import ResearchStateKey, StateNamespace


def _safe_truncate(text: str, limit: int = 500) -> str:
    text = (text or "").replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + f"... <truncated {len(text) - limit} chars>"


def _format_event(ev: Any) -> str:
    """Best-effort compact event formatting.

    We avoid dumping full chat histories/tool payloads, which can be extremely large.
    """

    name = type(ev).__name__

    delta = getattr(ev, "delta", None)
    if delta is not None:
        return f"{name} delta={_safe_truncate(str(delta), limit=200)}"

    tool_name = getattr(ev, "tool_name", None)
    if tool_name is not None:
        tool_kwargs = getattr(ev, "tool_kwargs", None)
        tool_id = getattr(ev, "tool_id", None)

        if name == "ToolCallResult":
            tool_output = getattr(ev, "tool_output", None)
            raw_output = getattr(tool_output, "raw_output", None) if tool_output else None
            is_error = getattr(tool_output, "is_error", None) if tool_output else None
            return (
                f"{name} tool_name={tool_name!r} tool_id={tool_id!r} "
                f"tool_kwargs={tool_kwargs} is_error={is_error} "
                f"raw_output={_safe_truncate(str(raw_output), limit=300)}"
            )

        return f"{name} tool_name={tool_name!r} tool_id={tool_id!r} tool_kwargs={tool_kwargs}"

    if name == "AgentInput":
        input_messages = getattr(ev, "input", None)
        if isinstance(input_messages, list) and input_messages:
            last = input_messages[-1]
            content = getattr(last, "content", None)
            if content is None and hasattr(last, "blocks") and last.blocks:
                content = getattr(last.blocks[0], "text", None)
            return f"{name} last_msg={_safe_truncate(str(content), limit=300)}"
        return f"{name}"

    if name == "AgentOutput":
        response = getattr(ev, "response", None)
        if response is not None:
            return f"{name} response={_safe_truncate(str(response), limit=200)}"
        return f"{name}"

    return f"{name} {ev}"


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

        events: list[object] = []
        try:
            async for ev in handler.stream_events():
                events.append(ev)
                print(f"Event: {_format_event(ev)}")
        except asyncio.CancelledError:
            print("\n(Event stream cancelled)")
            raise

        result = await handler
        print("\n🤖 Response:\n")
        print(str(result.response))
        print(f"\n(Collected {len(events)} events)")

        state = await ctx.store.get_state()
        _print_state_snapshot(state)


if __name__ == "__main__":
    asyncio.run(main())
