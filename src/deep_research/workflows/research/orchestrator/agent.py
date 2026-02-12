from llama_index.core.agent.workflow import FunctionAgent
from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent
from llama_index.core.tools import FunctionTool
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.workflows.research.state import DeepResearchState, ResearchArtifactStatus, ResearchStateAccessor
from deep_research.workflows.research.orchestrator.prompts import build_orchestrator_system_prompt

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.writer.agent import workflow as writer_agent

cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)
llm_cfg = cfg.orchestrator.main_llm
llm = GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)


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


research_tool = FunctionTool.from_defaults(fn=call_research_agent)
write_tool = FunctionTool.from_defaults(fn=call_write_agent)

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

        dynamic_system_prompt = build_orchestrator_system_prompt(current_state)

        agent = FunctionAgent(
            name="Orchestrator",
            description="Manages the report generation process.",
            system_prompt=dynamic_system_prompt,
            llm=llm,
            tools=[research_tool, write_tool],
        )

        result = await agent.run(user_msg="Start the research", ctx=ctx)
        return StopEvent(result=result)

workflow = OrchestratorWorkflow(timeout=None)
