from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.google_genai import GoogleGenAI
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from deep_research.workflows.research.writer.tools import WriterTools


cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)
writer_cfg = cfg.writer

llm = GoogleGenAI(
    model=writer_cfg.main_llm.model,
    temperature=writer_cfg.main_llm.temperature
)

tools_spec = WriterTools(config=cfg)
tools = tools_spec.to_tool_list()

system_prompt = """You are an expert technical writer.
Your goal is to write and update a comprehensive markdown report based on the provided research notes.

Tools:
- `apply_patch`: Update the report content by providing a valid patch (diff).
- `review_patch`: If review passes, commit the draft to the main report. Else, request new writes.

Critical constraint:
- The report file is `artifacts/report.md`.
- Your patch MUST use `*** Update File: artifacts/report.md` (not `report.md`).
- Do not add, delete, move, or rename files.

Instructions:
1. Read the research notes and any review feedback.
2. Determine what changes are needed in the report.
3. Use `apply_patch` to apply those changes.
4. IMMEDIATELY use `review_patch` to commit the draft to the main report or write again in case of errors.
5. Do NOT output the full report in your response. Only use the tools.
"""

workflow = FunctionAgent(
    name="WriterAgent",
    description="An agent capable of writing and updating reports.",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
    timeout=None,
)
