import re

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context, StartEvent, StopEvent, step, Workflow
from llama_index.core.tools import FunctionTool
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.workflows.research.state_keys import (
    OrchestratorStateKey,
    StateNamespace,
    ReportStateKey,
    ReportStatus,
    ResearchStateKey,
)
from deep_research.workflows.research.orchestrator.prompts import build_orchestrator_system_prompt

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.writer.agent import workflow as writer_agent
from deep_research.workflows.research.reviewer.agent import workflow as reviewer_agent

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

    result = await searcher_agent.run(
        user_msg=f"Write some notes about the following: {prompt}",
        ctx=ctx,
    )

    async with ctx.store.edit_state() as state:
        orch = state[StateNamespace.ORCHESTRATOR]
        note_entry = f"### Research on '{prompt}':\n{result.response}\n"
        orch[OrchestratorStateKey.RESEARCH_NOTES].append(note_entry)

    return str(result.response)


async def call_write_agent(ctx: Context, instruction: str) -> str:
    print(f"Orchestrator -> WriteAgent: {instruction}")

    state = await ctx.store.get_state()
    orch = state[StateNamespace.ORCHESTRATOR]
    notes = orch[OrchestratorStateKey.RESEARCH_NOTES]
    review_feedback = orch[OrchestratorStateKey.REVIEW]

    if not notes:
        return "No research notes to write from."

    user_msg = "Write a markdown report from the following notes. Be sure to output the report in the following format: <report>...</report>:\n\n"

    if review_feedback:
        user_msg += f"<feedback>{review_feedback}</feedback>\n\n"

    notes_str = "\n\n".join(notes)
    user_msg += f"<research_notes>{notes_str}</research_notes>\n\n"
    user_msg += f"Instruction: {instruction}"

    result = await writer_agent.run(user_msg=user_msg, ctx=ctx)

    match = re.search(r"<report>(.*)</report>", str(result.response), re.DOTALL)
    if not match:
        return "Writer produced output but missed <report> tags."

    report_content = match.group(1).strip()
    async with ctx.store.edit_state() as s:
        s[StateNamespace.REPORT][ReportStateKey.CONTENT] = report_content
    return "Report updated."


async def call_review_agent(ctx: Context, instructions: str = "Review the report") -> str:
    print(f"Orchestrator -> ReviewAgent: {instructions}")
    
    state = await ctx.store.get_state()
    report = state[StateNamespace.REPORT][ReportStateKey.CONTENT]

    result = await reviewer_agent.run(
        user_msg=f"{instructions}\n\nReport Content:\n{report}",
        ctx=ctx,
    )

    async with ctx.store.edit_state() as s:
        orch = s[StateNamespace.ORCHESTRATOR]
        orch[OrchestratorStateKey.REVIEW] = str(result.response)

    return str(result.response)


research_tool = FunctionTool.from_defaults(fn=call_research_agent)
write_tool = FunctionTool.from_defaults(fn=call_write_agent)
review_tool = FunctionTool.from_defaults(fn=call_review_agent)

class OrchestratorWorkflow(Workflow):
    """
    Wrapper workflow that constructs a fresh Orchestrator Agent for each run,
    injecting the current state (Report + Evidence) into the system prompt.
    """
    
    @step
    async def run_orchestrator(self, ev: StartEvent, ctx: Context) -> StopEvent:
        async with ctx.store.edit_state() as state:
            if StateNamespace.ORCHESTRATOR not in state:
                state[StateNamespace.ORCHESTRATOR] = {
                    OrchestratorStateKey.RESEARCH_NOTES: [],
                    OrchestratorStateKey.REVIEW: None,
                }
            if StateNamespace.RESEARCH not in state:
                state[StateNamespace.RESEARCH] = {
                    ResearchStateKey.SEEN_URLS: [],
                    ResearchStateKey.PENDING_EVIDENCE: {
                        "queries": [],
                        "directive": "",
                        "items": [],
                    },
                    ResearchStateKey.FOLLOW_UP_QUERIES: [],
                }
            if StateNamespace.REPORT not in state:
                state[StateNamespace.REPORT] = {
                    ReportStateKey.PATH: "artifacts/report.md",
                    ReportStateKey.CONTENT: "",
                    ReportStateKey.STATUS: ReportStatus.RUNNING,
                }

        state = await ctx.store.get_state()
        dynamic_system_prompt = build_orchestrator_system_prompt(state)
        
        agent = FunctionAgent(
            name="Orchestrator",
            description="Manages the report generation process.",
            system_prompt=dynamic_system_prompt,
            llm=llm,
            tools=[research_tool, write_tool, review_tool],
        )
        
        result = await agent.run(user_msg=str(ev.user_msg or "Proceed with the next step."))
        return StopEvent(result=result)

workflow = OrchestratorWorkflow(timeout=None)
