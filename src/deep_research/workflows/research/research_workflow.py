from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from deep_research.config import ResearchConfig

from deep_research.tools.demo_tools import DemoTools
from deep_research.tools.mock_tools import MockTools


cfg = ResearchConfig()
llm_cfg = cfg.llm

# Initialize LLM
llm = OpenAI(
    model=llm_cfg.model,
    temperature=llm_cfg.temperature,
    reasoning_effort=llm_cfg.reasoning_effort,
)

# Initialize Tools
tools = []
tools.extend(DemoTools().to_tool_list())
tools.extend(MockTools().to_tool_list())

# Create FunctionAgent
workflow = FunctionAgent(
    name="ResearchAgent",
    description="An agent capable of performing deep research tasks with HITL support.",
    system_prompt="You are a helpful research assistant. You can use tools to perform tasks and ask for human confirmation when necessary.",
    llm=llm,
    tools=tools,
)
