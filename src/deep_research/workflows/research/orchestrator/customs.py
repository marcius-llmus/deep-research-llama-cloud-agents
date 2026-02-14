from typing import List, Sequence
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.tools import AsyncBaseTool
from llama_index.core.agent.workflow import FunctionAgent, AgentOutput
from workflows import Context

from deep_research.workflows.research.orchestrator.prompts import build_orchestrator_system_prompt
from deep_research.workflows.research.state import ResearchStateAccessor

# note, specifically for orchestrator, it is not interesting to keep the whole report building up in chat history
# by using a hot system message, we refresh the system message based on state. sadly, it kills caching, but considering
# the nature of extremely dynamic nature of research reports, it is acceptable.
# sub agents will also communicate though state, but tools share state so the tool itself can read the state of what it
# wants / need to change. so the tools themselves guide the agent on how to proceed because they read the states.
# here it is different. the orchestrator tools (the sub agents) won't share context they should not know each other
# they obviously share the context, but they won't communicate. this responsibility goes to the agent itself (the llm)
# and the only way of doing this is everytime a sub agent returns, it tells the llm that it changed state, and it
# acts based on hot system message: sub agent change state, orchestrator read new state and decides what to do next
# this hack is SPECIFICALLY for ORCHESTRATOR

class OrchestratorAgent(FunctionAgent):
    async def take_step(
        self,
        ctx: Context,
        llm_input: List[ChatMessage],
        tools: Sequence[AsyncBaseTool],
        memory: BaseMemory,
    ) -> AgentOutput:
        state = await ResearchStateAccessor.get(ctx)
        hot_system_prompt = build_orchestrator_system_prompt(
            research_plan=state.orchestrator.research_plan,
            actual_research=state.research_artifact.content,
            evidence_summary=state.research_turn.evidence.get_summary(),
        )

        if not llm_input or llm_input[0].role != "system":
            raise ValueError("OrchestratorAgent expects a system message at index 0.")

        llm_input[0].content = hot_system_prompt
        return await super().take_step(ctx, llm_input, tools, memory)
