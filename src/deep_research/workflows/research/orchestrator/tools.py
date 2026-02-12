from workflows import Context
from deep_research.workflows.research.state import ResearchStateAccessor
from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.writer.agent import workflow as writer_agent



async def call_research_agent(ctx: Context, prompt: str) -> str:
    print(f"Orchestrator -> SearcherAgent: {prompt}")

    await searcher_agent.run(
        user_msg=f"Write some notes about the following: {prompt}",
        ctx=ctx,
    )

    state = await ResearchStateAccessor.get(ctx)
    return state.research_turn.evidence.get_summary()


async def call_write_agent(ctx: Context, instruction: str) -> str:
    print(f"Orchestrator -> WriteAgent: {instruction}")

    state = await ResearchStateAccessor.get(ctx)
    evidence_text = state.research_turn.evidence.get_content_for_writing()

    user_msg = "Update the report based on the following research notes and instructions.\n\n"
    user_msg += f"Research Notes:\n<research_notes>{evidence_text}</research_notes>\n\n"
    user_msg += f"Instruction: {instruction}"

    result = await writer_agent.run(user_msg=user_msg, ctx=ctx)

    return str(result.response)
