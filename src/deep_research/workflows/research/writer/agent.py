from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from deep_research.config import ResearchConfig
from deep_research.workflows.research.writer.tools import get_writer_tools

cfg = ResearchConfig()
llm_cfg = cfg.llm

llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)

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
    tools=get_writer_tools(config=cfg),
)
