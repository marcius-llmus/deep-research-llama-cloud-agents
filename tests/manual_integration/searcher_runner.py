import asyncio
import json
from typing import Any

from workflows import Context

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.state import DeepResearchState, ResearchArtifactStatus


def _redact_tool_kwargs(tool_kwargs: Any) -> Any:
    if not isinstance(tool_kwargs, dict):
        return tool_kwargs
    redacted = tool_kwargs.copy()
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


async def _reset_searcher_state(ctx: Context[DeepResearchState]) -> None:
    async with ctx.store.edit_state() as state:
        state.orchestrator.research_plan = ""
        state.research_turn.clear()
        state.research_artifact.content = ""
        state.research_artifact.draft_content = ""
        state.research_artifact.status = ResearchArtifactStatus.RUNNING


def _print_state_snapshot(state: DeepResearchState) -> None:
    seen_urls = state.research_turn.seen_urls
    items = state.research_turn.evidence.items
    follow_ups = state.research_turn.follow_up_queries

    print("\n--- State snapshot ---")
    print(f"seen_urls: {len(seen_urls)}")
    print(f"pending_evidence.items: {len(items)}")
    print(f"follow_up_queries: {len(follow_ups)}")


async def main() -> None:
    ctx = Context(searcher_agent)

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
            await _reset_searcher_state(ctx)
            print("Reset research state.")
            continue

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
