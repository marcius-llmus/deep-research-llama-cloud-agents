import uuid
from typing import Annotated, Union

from llama_cloud import AsyncLlamaCloud
from llama_index.core.agent.utils import generate_structured_response
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import BaseMemory, ChatMemoryBuffer
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent, StopEvent
from workflows import Context, Workflow, step
from workflows.resource import Resource, ResourceConfig

from .clients import agent_name, get_llama_cloud_client
from .config import ResearchConfig
from .events import PlannerTurnEvent, PlannerOutputEvent, PlanStartEvent
from llama_index.llms.openai import OpenAI

from .llm import get_planner_llm_resource
from .schemas import PlannerAgentOutput, ResearchPlanState



class DeepResearchPlanWorkflow(Workflow):
    _SYSTEM_PROMPT = (
        "You are an expert deep-research planner collaborating with a human.\n\n"
        "Goal: produce a high-quality research plan through HITL iterations.\n\n"
        "You MUST output a valid JSON object that matches the PlannerAgentOutput schema.\n\n"
        "Your job: convert the user's request into a compact research plan as questions we will research.\n\n"
        "Output requirements:\n"
        "- Do NOT list sources, databases, tools, or institutions.\n"
        "- Do NOT write a methodology or step-by-step procedure.\n"
        "- The plan MUST be 3-5 bullet points and EACH bullet must be a QUESTION.\n"
        "- Keep it short: <= 80 words total for the plan, unless user proposes it to be bigger.\n\n"
        "Constraints:\n"
        "- Plan bullets must be ABOUT THE TOPIC (the actual research questions), not meta-questions about\n"
        "  how to measure/define the topic. Do not use the plan bullets to ask the user to choose a metric,\n"
        "  year, thresholds, regions, etc.\n"
        "- If key details are missing, do BOTH of the following:\n"
        "  (1) In response: ask 1-3 clarifying questions for the user.\n"
        "  (2) In plan: still propose a best-effort plan using explicit reasonable default assumptions\n"
        "      (e.g., latest year available; worldwide; GDP per capita PPP; include/exclude microstates),\n"
        "      and ensure every bullet remains a topic research question.\n\n"
        "Decision policy (HITL):\n"
        "- decision='propose_plan': Present a plan (initial or revised) for user review.\n"
        "- decision='finalize': Use this when user agrees with the plan.\n"
        "  This is the TERMINAL step. The workflow will end here.\n"
        "- If details are missing in the query, ask clarifying questions in response, and propose the best plan you can.\n"
        "- The plan MUST be returned as raw text in plan (not JSON).\n"
    )

    @step
    async def init_session(
        self,
        ctx: Context,
        ev: PlanStartEvent,
        planner_llm: Annotated[OpenAI, Resource(get_planner_llm_resource)],
    ) -> PlannerTurnEvent:
        """Initialize run state and memory buffer once, then convert into a turn."""

        initial_query = ev.initial_query

        async with ctx.store.edit_state() as state:
            state.initial_query = initial_query
            state.research_id = str(uuid.uuid4())
            state.status = "planning"

        await ctx.store.set("memory", ChatMemoryBuffer.from_defaults(llm=planner_llm))

        return PlannerTurnEvent(message=initial_query)

    @step
    async def run_planner_llm(
        self,
        ctx: Context,
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
        return PlannerOutputEvent(output=output, user_message=ev.message) # noqa

    @step
    async def apply_plan_update(
        self,
        ctx: Context,
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
        """Apply plan updates, stream plan to UI, and either continue HITL or finalize."""

        memory: BaseMemory = await ctx.store.get("memory")
        await memory.aput(ChatMessage(role="user", content=ev.user_message))
        await memory.aput(ChatMessage(role="assistant", content=ev.output.response))

        async with ctx.store.edit_state() as state:
            state.plan_text = ev.output.plan

        if ev.output.decision != "finalize":
            prefix = (
                f"Current Plan:\n{ev.output.plan}\n\n"
                f"You can improve the research plan answering these questions:\n{ev.output.response}\n\n"
                "Type 'accept' to approve, or reply with edits."
            )
            return InputRequiredEvent(prefix=prefix)  # noqa

        return await self._finalize_run(ctx, llama_cloud_client, research_config)

    async def _finalize_run(
        self,
        ctx: Context,
        llama_cloud_client: AsyncLlamaCloud,
        research_config: ResearchConfig,
    ) -> StopEvent:
        """Helper to finalize state, persist, and stop the workflow."""
        async with ctx.store.edit_state() as state:
            state.status = "finalized"
        
        final_state = await ctx.store.get_state()
        plan_text = final_state.plan_text
        
        item_id = await self._persist_session(
            llama_cloud_client=llama_cloud_client,
            research_config=research_config,
            state=final_state,
            plan_text=plan_text,
        )

        return StopEvent(
            result={
                "research_id": final_state.research_id,
                "status": final_state.status,
                "agent_data_id": item_id,
                "plan": plan_text,
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
            filter={"research_id": {"eq": state.research_id}}, # noqa
        )
        item = await llama_cloud_client.beta.agent_data.agent_data(
            data=record,
            deployment_name=agent_name or "_public",
            collection=research_config.collections.research_collection,
        )
        return item.id

    @step
    async def on_human_response(
        self,
        ctx: Context,
        ev: HumanResponseEvent,
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
    ) -> Union[PlannerTurnEvent, StopEvent]:
        """Handle user input. If 'accept', persist and stop. Otherwise, continue planning."""

        normalized = ev.response.strip().lower()
        if normalized == "accept":
            state: ResearchPlanState = await ctx.store.get_state()
            if not state.plan_text:
                return PlannerTurnEvent(message=ev.response)

            return await self._finalize_run(ctx, llama_cloud_client, research_config)

        return PlannerTurnEvent(message=ev.response)


workflow = DeepResearchPlanWorkflow(timeout=None)
