import uuid
from typing import Annotated, Union

from llama_cloud import AsyncLlamaCloud
from llama_index.core.agent.utils import generate_structured_response
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import BaseMemory, ChatMemoryBuffer
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent, StopEvent
from workflows.events import StartEvent
from workflows import Context, Workflow, step
from workflows.resource import Resource, ResourceConfig

from .clients import agent_name, get_llama_cloud_client
from .config import ResearchConfig
from .events import PlannerFinalPlanEvent, PlannerTurnEvent, PlannerOutputEvent
from llama_index.llms.openai import OpenAI

from .llm import get_planner_llm_resource
from .schemas import PlannerAgentOutput, ResearchPlanState



class DeepResearchPlanWorkflow(Workflow):
    _SYSTEM_PROMPT = (
        "You are an expert deep-research planner collaborating with a human.\n\n"
        "Goal: produce a high-quality research plan through HITL iterations.\n\n"
        "You MUST output a valid JSON object that matches the PlannerAgentOutput schema.\n\n"
        "Process:\n"
        "- Ask a clarifying question if needed (exactly ONE question).\n"
        "- Otherwise, propose a research plan and ask if it looks good or if the user wants to add/change anything.\n"
        "- If the user approves explicitly, finalize immediately.\n\n"
        "Hard rules:\n"
        "- decision='ask_question' => response is ONLY the question. plan must be null.\n"
        "- decision='propose_plan' => include a plan and end response with an approval question.\n"
        "- decision='finalize' => ONLY after explicit approval (e.g. 'yes', 'approved', 'looks good').\n"
        "- The plan MUST be returned as raw text in plan (not JSON).\n"
        "- Keep the plan concise but specific: questions to clarify, expanded queries, outline, assumptions.\n"
    )

    @step
    async def init_session(
        self,
        ctx: Context[ResearchPlanState],
        ev: StartEvent,
        planner_llm: Annotated[OpenAI, Resource(get_planner_llm_resource)],
    ) -> PlannerTurnEvent:
        """Initialize run state and memory buffer once, then convert into a turn."""

        initial_query = ev.get("initial_query")
        if not isinstance(initial_query, str) or not initial_query.strip():
            raise ValueError("start_event.initial_query must be a non-empty string")

        async with ctx.store.edit_state() as state:
            state.initial_query = initial_query
            state.research_id = str(uuid.uuid4())
            state.status = "planning"

        await ctx.store.set("memory", ChatMemoryBuffer.from_defaults(llm=planner_llm))

        return PlannerTurnEvent(message=initial_query)

    @step
    async def run_planner_llm(
        self,
        ctx: Context[ResearchPlanState],
        ev: PlannerTurnEvent,
        planner_llm: Annotated[OpenAI, Resource(get_planner_llm_resource)],
    ) -> PlannerOutputEvent:
        """Run the LLM and parse a structured PlannerAgentOutput."""

        memory: BaseMemory = await ctx.store.get("memory")
        history = await memory.aget()

        messages = [
            ChatMessage(role="system", content=self._SYSTEM_PROMPT),
            *history,
            ChatMessage(role="user", content=ev.message),
        ]

        output = await generate_structured_response(
            messages=messages, llm=planner_llm, output_cls=PlannerAgentOutput
        )
        return PlannerOutputEvent(output=output, user_message=ev.message)

    @step
    async def apply_plan_update(
        self,
        ctx: Context[ResearchPlanState],
        ev: PlannerOutputEvent,
    ) -> PlannerOutputEvent:
        """Apply any plan updates into workflow state and stream plan to UI."""

        memory: BaseMemory = await ctx.store.get("memory")
        await memory.aput(ChatMessage(role="user", content=ev.user_message))
        await memory.aput(ChatMessage(role="assistant", content=ev.output.response))

        ctx.write_event_to_stream(
            PlannerFinalPlanEvent(plan={"text": ev.output.plan})
        )

        return ev

    @step
    async def decide_next(
        self,
        ctx: Context[ResearchPlanState],
        ev: PlannerOutputEvent,
        llama_cloud_client: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        research_config: Annotated[
            ResearchConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="research",
                label="Research Config",
                description="Deep research collection + settings",
            ),
        ],
    ) -> Union[InputRequiredEvent, StopEvent]:
        """Return HITL request or finalize/persist."""

        # finalize immediately when the model says it's finalized (explicit approval detected)
        if ev.output.decision != "finalize":
            return InputRequiredEvent(prefix=ev.output.response)

        async with ctx.store.edit_state() as new_state:
            new_state.status = "awaiting_approval"

        final_state = await ctx.store.get_state()
        item_id = await self._persist_session(
            llama_cloud_client=llama_cloud_client,
            research_config=research_config,
            state=final_state,
            plan_text=ev.output.plan,
        )

        return StopEvent(
            result={
                "research_id": final_state.research_id,
                "status": final_state.status,
                "agent_data_id": item_id,
                "plan": ev.output.plan,
            }
        )

    @staticmethod
    async def _persist_session(
        *,
        llama_cloud_client: AsyncLlamaCloud,
        research_config: ResearchConfig,
        state: ResearchPlanState,
        plan_text: str | None,
    ) -> str:
        """Persist the session record idempotently and return agent_data item id."""

        if state.research_id is None:
            raise ValueError("research_id must be set before persistence")

        record = {
            "research_id": state.research_id,
            "status": state.status,
            "initial_query": state.initial_query,
            "plan": plan_text,
        }

        await llama_cloud_client.beta.agent_data.delete_by_query(
            deployment_name=agent_name or "_public",
            collection=research_config.collections.research_collection,
            filter={"research_id": {"eq": state.research_id}},
        )
        item = await llama_cloud_client.beta.agent_data.agent_data(
            data=record,
            deployment_name=agent_name or "_public",
            collection=research_config.collections.research_collection,
        )
        return item.id

    @step
    async def on_human_response(
        self, _: Context[ResearchPlanState], ev: HumanResponseEvent
    ) -> PlannerTurnEvent:
        """Convert HumanResponseEvent into the internal PlannerTurnEvent."""
        return PlannerTurnEvent(message=ev.response)


workflow = DeepResearchPlanWorkflow(timeout=None)
