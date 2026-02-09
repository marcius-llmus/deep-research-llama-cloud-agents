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
llm_cfg = cfg.writer.main_llm
llm = GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)

tools_spec = WriterTools(config=cfg)
tools = tools_spec.to_tool_list()

system_prompt = (
    "You are an expert technical writer.\n"
    "You will be given research notes, a current report draft (if any), and feedback.\n"
    "Your task is to write or update the report based on this information.\n"
    "IMPORTANT: You MUST wrap the full report markdown content in <report>...</report> tags.\n"
    "Do not include the <report> tags in your normal conversation, only around the final artifact."
)

workflow = FunctionAgent(
    name="WriterAgent",
    description="An agent capable of writing reports",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
)
