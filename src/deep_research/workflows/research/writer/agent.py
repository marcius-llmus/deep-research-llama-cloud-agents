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

system_prompt = "You are an expert technical writer. Your goal is to write a comprehensive report based on the provided research notes."

workflow = FunctionAgent(
    name="WriterAgent",
    description="An agent capable of writing and updating reports.",
    system_prompt=system_prompt,
    llm=llm,
    tools=tools,
)
