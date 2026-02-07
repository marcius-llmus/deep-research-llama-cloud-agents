import asyncio

from deep_research.workflows.planner.events import PlanStartEvent
from deep_research.workflows.planner.planner_workflow import DeepResearchPlanWorkflow
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent


async def main():
    workflow = DeepResearchPlanWorkflow(timeout=None)

    handler = workflow.run(
        start_event=PlanStartEvent(
            initial_query=input("👤 You: ")
        )
    )
    
    async for ev in handler.stream_events():
        if isinstance(ev, InputRequiredEvent):
            print(f"\n🤖 Bot: {ev.prefix}")
            response = input("👤 You: ")
            handler.ctx.send_event(HumanResponseEvent(response=response))
        else:
            print(f"Event: {ev}")

    result = await handler
    print(f"\n🏁 Workflow Finished. Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
