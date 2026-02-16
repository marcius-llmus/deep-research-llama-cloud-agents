from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent
from llama_index.core.tools import FunctionTool
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.workflows.research.orchestrator.customs import OrchestratorAgent
from deep_research.workflows.research.orchestrator.tools import call_research_agent, call_write_agent
from deep_research.workflows.research.state import ResearchStateAccessor
from deep_research.workflows.research.orchestrator.prompts import build_orchestrator_system_prompt


cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)


def build_orchestrator_agent(dynamic_system_prompt) -> OrchestratorAgent:
    llm_cfg = cfg.orchestrator.main_llm
    llm = GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)

    research_tool = FunctionTool.from_defaults(fn=call_research_agent)
    write_tool = FunctionTool.from_defaults(fn=call_write_agent)

    return OrchestratorAgent(
        name="Orchestrator",
        description="Manages the report generation process.",
        system_prompt=dynamic_system_prompt,
        llm=llm,
        tools=[research_tool, write_tool],
    )

class OrchestratorWorkflow(Workflow):
    """
    Wrapper workflow that constructs a fresh Orchestrator Agent for each run,
    injecting the current state (Report + Evidence) into the system prompt.
    """

    @step
    async def run_orchestrator(self, ctx: Context, ev: StartEvent) -> StopEvent:
        plan_text = str(ev.user_msg)

        async with ResearchStateAccessor.edit(ctx) as state:
            state.orchestrator.research_plan = plan_text
            current_state = state.model_copy()

        dynamic_system_prompt = build_orchestrator_system_prompt( # noqa
            research_plan=current_state.orchestrator.research_plan,
            actual_research=current_state.research_artifact.content,
            evidence_summary=current_state.research_turn.evidence.get_summary(),
        )

        agent = build_orchestrator_agent(dynamic_system_prompt)

        agent_ctx = Context(agent)
        async with agent_ctx.store.edit_state() as store:
            store[ResearchStateAccessor.KEY] = current_state.model_dump()

        handler = agent.run(user_msg="Start the research", ctx=agent_ctx)

        async for event in handler.stream_events():
            ctx.write_event_to_stream(event)

        result = await handler

        final_inner_state = await ResearchStateAccessor.get(agent_ctx)
        async with ctx.store.edit_state() as store:
            store[ResearchStateAccessor.KEY] = final_inner_state.model_dump()

        return StopEvent(result=result)

workflow = OrchestratorWorkflow(timeout=None)
