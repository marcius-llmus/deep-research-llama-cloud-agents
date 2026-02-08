from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json
from deep_research.workflows.research.searcher.tools import SearcherTools
from deep_research.workflows.research.searcher.prompts import build_research_system_prompt
from deep_research.services.research_llm_service import ResearchLLMService
from deep_research.services.web_search_service import WebSearchService

cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)
llm_cfg = cfg.llm

llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)

tools_spec = SearcherTools(
    config=cfg,
    web_search_service=WebSearchService(),
    llm_service=ResearchLLMService(),
)
tools = tools_spec.to_tool_list()
system_prompt = build_research_system_prompt(cfg)

workflow = FunctionAgent(
    name="SearcherAgent",
    description="An agent capable of performing deep research tasks with HITL support.",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
)
