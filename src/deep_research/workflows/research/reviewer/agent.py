from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from deep_research.config import ResearchConfig

cfg = ResearchConfig()
llm_cfg = cfg.llm

llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)

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
    tools=[],
)
