import json
from pathlib import Path
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from .tools.demo_tools import DemoTools
from .tools.mock_tools import MockTools

# Load configuration
root = Path(__file__).resolve().parent.parent.parent
config_path = root / "configs" / "config.json"

with open(config_path, "r") as f:
    config_data = json.load(f)

research_config = config_data.get("research", {})
llm_config = research_config.get("llm", {})

# Initialize LLM
llm = OpenAI(
    model="gpt-4.1-mini",
    temperature=llm_config.get("temperature", 0.1),
    # reasoning_effort is only supported by some models/versions
    #reasoning_effort=llm_config.get("reasoning_effort", "low"),
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
