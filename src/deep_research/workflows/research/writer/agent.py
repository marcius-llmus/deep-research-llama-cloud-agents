from llama_index.core.tools import FunctionTool
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from deep_research.workflows.research.writer.customs import WriterAgent
from deep_research.workflows.research.writer.prompts import WRITER_SYSTEM_PROMPT
from deep_research.workflows.research.writer.tools import WriterTools


cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)


def build_writer_agent(*, system_prompt: str = WRITER_SYSTEM_PROMPT) -> WriterAgent:
    writer_cfg = cfg.writer

    llm = GoogleGenAI(
        model=writer_cfg.main_llm.model,
        temperature=writer_cfg.main_llm.temperature,
        reasoning={"thinking_level": "HIGH"},
    )

    tools_spec = WriterTools(config=cfg)
    tools = tools_spec.to_tool_list()

    finish_tool = FunctionTool.from_defaults(
        fn=tools_spec.finish_writing,
        return_direct=True,
    )
    tools.append(finish_tool)

    return WriterAgent(
        name="WriterAgent",
        description="An agent capable of writing and updating reports.",
        system_prompt=system_prompt,
        llm=llm,
        tools=tools,
        timeout=None,
    )
