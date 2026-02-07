from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from deep_research.config import ResearchConfig
from deep_research.workflows.research.tools.research_tools import ResearchTools
from deep_research.workflows.research.prompts import build_research_system_prompt

cfg = ResearchConfig()
llm_cfg = cfg.llm


llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)

tools = ResearchTools(config=cfg, llm=llm).to_tool_list()


system_prompt = build_research_system_prompt(cfg)


workflow = FunctionAgent(
    name="ResearchAgent",
    description="An agent capable of performing deep research tasks with HITL support.",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
)
