from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.google_genai import GoogleGenAI
from deep_research.config import ResearchConfig
from deep_research.utils import load_config_from_json

cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)
llm_cfg = cfg.reviewer.main_llm
llm = GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)

tools = []

system_prompt = (
    "You are a critical reviewer.\n"
    "Review the provided report for accuracy, clarity, structure, and completeness.\n"
    "Provide constructive feedback and list missing points if any."
)

workflow = FunctionAgent(
    name="ReviewerAgent",
    description="An agent capable of reviewing reports",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
)
