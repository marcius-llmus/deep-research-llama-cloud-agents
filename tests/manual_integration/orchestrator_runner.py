import asyncio
import json
from typing import Any

from workflows import Context
from deep_research.workflows.research.orchestrator.agent import workflow as orchestrator_workflow
from deep_research.workflows.research.state import DeepResearchState

def _format_event(ev: Any) -> str | None:
    return f"{type(ev).__name__}: {ev}"


def _print_snapshot(state: DeepResearchState | None) -> None:
    if state is None:
        print("\n--- Snapshot (Empty) ---")
        return

    content = state.research_artifact.content
    draft = state.research_artifact.turn_draft
    items = state.research_turn.evidence.items
    plan = state.orchestrator.research_plan

    print("\n--- Snapshot ---")
    print(f"Plan length: {len(plan)} chars")
    print(f"Report length: {len(content)} chars")
    print(f"Draft length: {len(draft)} chars")
    print(f"Pending evidence items: {len(items)}")


async def main():
    ctx = Context(orchestrator_workflow)

    print("Orchestrator E2E runner. Commands: /state /state_json /exit")
    while True:
        user_msg = input("\n👤 Orchestrator instruction: ").strip()
        if not user_msg:
            continue
        if user_msg in {"/exit", "/quit"}:
            break
        if user_msg == "/state":
            state = await ctx.store.get_state()
            _print_snapshot(state)
            continue
        if user_msg == "/state_json":
            state = await ctx.store.get_state()
            print(json.dumps(state, indent=2, default=str))
            continue

        handler = orchestrator_workflow.run(user_msg=user_msg, ctx=ctx)

        async for ev in handler.stream_events():
            msg = _format_event(ev)
            if msg:
                print("Event:", msg)

        result = await handler
        print("\nResult:", result)

        state = await ctx.store.get_state()
        _print_snapshot(state)

if __name__ == "__main__":
    asyncio.run(main())
