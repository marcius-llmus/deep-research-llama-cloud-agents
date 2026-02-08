import re
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI

from deep_research.config import ResearchConfig

from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.writer.agent import workflow as writer_agent
from deep_research.workflows.research.reviewer.agent import workflow as reviewer_agent

cfg = ResearchConfig()
llm_cfg = cfg.llm

llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)


async def call_research_agent(ctx: Context, prompt: str) -> str:
    """Useful for recording research notes based on a specific prompt."""
    print(f"Orchestrator -> ResearchAgent: {prompt}")
    
    result = await searcher_agent.run(
        user_msg=f"Write some notes about the following: {prompt}"
    )

    async with ctx.store.edit_state() as state:
        current_notes = state.get("research_notes", [])
        note_entry = f"### Research on '{prompt}':\n{result.response}\n"
        current_notes.append(note_entry)
        state["research_notes"] = current_notes

    return str(result.response)

async def call_write_agent(ctx: Context, instruction: str) -> str:
    """Useful for writing a report based on the research notes or revising the report based on feedback."""
    print(f"Orchestrator -> WriteAgent: {instruction}")

    state = await ctx.store.get_state()
    notes = state.get("research_notes", [])
    review_feedback = state.get("review", None)

    if not notes:
        return "No research notes to write from."

    user_msg = f"Write a markdown report from the following notes. Be sure to output the report in the following format: <report>...</report>:\n\n"

    if review_feedback:
        user_msg += f"<feedback>{review_feedback}</feedback>\n\n"

    notes_str = "\n\n".join(notes)
    user_msg += f"<research_notes>{notes_str}</research_notes>\n\n"
    user_msg += f"Instruction: {instruction}"

    result = await writer_agent.run(user_msg=user_msg)

    match = re.search(r"<report>(.*)</report>", str(result.response), re.DOTALL)
    if match:
        report_content = match.group(1).strip()
        async with ctx.store.edit_state() as s:
            s["report_content"] = report_content
        return "Report updated."
    else:
        return "Writer produced output but missed <report> tags."

async def call_review_agent(ctx: Context) -> str:
    """Useful for reviewing the report and providing feedback."""
    print(f"Orchestrator -> ReviewAgent")

    state = await ctx.store.get_state()
    report = state.get("report_content")

    if not report:
        return "No report content to review."

    result = await reviewer_agent.run(
        user_msg=f"Review the following report: {report}"
    )

    async with ctx.store.edit_state() as s:
        s["review"] = str(result.response)

    return str(result.response)


workflow = FunctionAgent(
    name="Orchestrator",
    description="Manages the report generation process.",
    system_prompt=(
        "You are an expert in the field of report writing. "
        "You are given a user request and a list of tools that can help with the request. "
        "You are to orchestrate the tools to research, write, and review a report on the given topic. "
        "Once the review is positive, you should notify the user that the report is ready to be accessed."
    ),
    llm=llm,
    tools=[
        FunctionTool.from_defaults(fn=call_research_agent),
        FunctionTool.from_defaults(fn=call_write_agent),
        FunctionTool.from_defaults(fn=call_review_agent),
    ],
    initial_state={
        "research_notes": [],
        "report_content": None,
        "review": None,
    }
)
