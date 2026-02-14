from typing import List, Sequence

from llama_index.core.agent.workflow import FunctionAgent, AgentOutput
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.tools import AsyncBaseTool
from workflows import Context

from deep_research.workflows.research.state import ResearchStateAccessor
from deep_research.workflows.research.writer.prompts import build_writer_hot_system_prompt


# this override is similar to orchestrator. The origin of this necessity is specific to big reports actually
# we can't be returning and passing huge reports
class WriterAgent(FunctionAgent):
    async def take_step(
        self,
        ctx: Context,
        llm_input: List[ChatMessage],
        tools: Sequence[AsyncBaseTool],
        memory: BaseMemory,
    ) -> AgentOutput:
        state = await ResearchStateAccessor.get(ctx)
        hot_system_prompt = build_writer_hot_system_prompt(
            original_report=state.research_artifact.content or "",
            evidences=state.research_turn.evidence.get_content_for_writing(),
            current_draft_report=state.research_artifact.turn_draft or state.research_artifact.content or "",
        )

        if not llm_input or llm_input[0].role != "system":
            raise ValueError("WriterAgent expects a system message at index 0.")

        llm_input[0].content = hot_system_prompt
        return await super().take_step(ctx, llm_input, tools, memory)
