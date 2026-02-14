from workflows import Context

from deep_research.workflows.research.state import ResearchStateAccessor
from deep_research.workflows.research.searcher.agent import build_searcher_agent
from deep_research.workflows.research.writer.agent import build_writer_agent



async def call_research_agent(ctx: Context, prompt: str) -> str:
    print(f"Orchestrator -> SearcherAgent: {prompt}")

    searcher_agent = build_searcher_agent()
    searcher_ctx = Context(searcher_agent)

    orchestrator_state = await ResearchStateAccessor.get(ctx)
    async with ResearchStateAccessor.edit(searcher_ctx) as searcher_state:
        searcher_state.orchestrator.research_plan = orchestrator_state.orchestrator.research_plan
        searcher_state.research_artifact = orchestrator_state.research_artifact.model_copy(deep=True)
        searcher_state.research_turn = orchestrator_state.research_turn.model_copy(deep=True)

    await searcher_agent.run(user_msg=prompt, ctx=searcher_ctx)

    searcher_state = await ResearchStateAccessor.get(searcher_ctx)

    async with ResearchStateAccessor.edit(ctx) as state:
        state.research_turn = searcher_state.research_turn.model_copy(deep=True)

    return searcher_state.research_turn.evidence.get_summary()


async def call_write_agent(ctx: Context, instruction: str) -> str:
    print(f"Orchestrator -> WriteAgent: {instruction}")

    orchestrator_state = await ResearchStateAccessor.get(ctx)

    writer_agent = build_writer_agent()
    writer_ctx = Context(writer_agent)

    # todo writer doesn't need all that
    async with ResearchStateAccessor.edit(writer_ctx) as writer_state:
        writer_state.orchestrator.research_plan = orchestrator_state.orchestrator.research_plan
        writer_state.research_artifact.content = orchestrator_state.research_artifact.content
        writer_state.research_artifact.turn_draft = orchestrator_state.research_artifact.content
        writer_state.research_artifact.status = orchestrator_state.research_artifact.status
        writer_state.research_artifact.path = orchestrator_state.research_artifact.path
        writer_state.research_turn = orchestrator_state.research_turn.model_copy(deep=True)

    result = await writer_agent.run(user_msg=f"Instruction: {instruction}", ctx=writer_ctx)

    new_report = result.response.content

    async with ResearchStateAccessor.edit(ctx) as state:
        state.research_artifact.content = new_report
        state.research_artifact.turn_draft = None
        state.research_turn.clear()

    return "Writing session finished. Report updated."
