import asyncio
import sys

from workflows import Context
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent, StopEvent, StartEvent

from deep_research.workflows.planner.workflow import DeepResearchPlanWorkflow
from deep_research.workflows.planner.events import PlanStartEvent
from deep_research.workflows.research.orchestrator.agent import OrchestratorWorkflow
from deep_research.workflows.research.state import ResearchStateAccessor


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "How does the world evolve?"
    print(f"Query: {query}")

    # --- PLANNER ---
    print("\n=== PLANNER ===\n")
    planner = DeepResearchPlanWorkflow(timeout=None)
    planner_ctx = Context(planner)

    handler = planner.run(start_event=PlanStartEvent(initial_query=query), ctx=planner_ctx)

    plan_text = ""

    async for ev in handler.stream_events():
        print(f"[Planner Event] {type(ev).__name__}")
        if isinstance(ev, InputRequiredEvent):
            print(ev.prefix)
            user_input = input("What do you think: ")
            planner_ctx.send_event(HumanResponseEvent(response=user_input))
        elif isinstance(ev, StopEvent):
            print("Planner finished.")
            result = ev.result
            if isinstance(result, dict) and "plan" in result:
                plan_text = result["plan"]
            else:
                plan_text = str(result)

    await handler

    print(f"\nPlan:\n{plan_text}\n")

    if not plan_text:
        print("No plan generated.")
        return

    # --- ORCHESTRATOR ---
    print("\n=== ORCHESTRATOR ===\n")
    orchestrator = OrchestratorWorkflow(timeout=None)
    orch_ctx = Context(orchestrator)

    orchestrator_handler = orchestrator.run(start_event=StartEvent(user_msg=plan_text), ctx=orch_ctx)

    async for ev in orchestrator_handler.stream_events():
        print(f"[Orchestrator Event] {type(ev).__name__}")
        if hasattr(ev, "tool_name"):
            print(f"  Tool: {ev.tool_name}")
            if hasattr(ev, "tool_kwargs"):
                print(f"  Args: {ev.tool_kwargs}")
        if hasattr(ev, "tool_output"):
            print(f"  Output: {str(ev.tool_output)[:200]}...")

    await orchestrator_handler
    state = await ResearchStateAccessor.get(orch_ctx)
    print("\n=== FINAL REPORT ===\n")
    print(state.research_artifact.content)

    with open("final_report.md", "w", encoding="utf-8") as f:
        f.write(state.research_artifact.content)
    print("\nSaved to final_report.md")


if __name__ == "__main__":
    asyncio.run(main())
