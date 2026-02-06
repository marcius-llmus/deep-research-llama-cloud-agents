import hashlib
import logging
from typing import Annotated

from llama_cloud import AsyncLlamaCloud
from workflows import Context, Workflow, step
from llama_index.core.workflow.events import HumanResponseEvent, InputRequiredEvent
from workflows.resource import Resource, ResourceConfig
from workflows.events import StartEvent
from .clients import agent_name, get_llama_cloud_client
from .config import ResearchConfig
from .events import (
    PlannerFinalPlanEvent,
    PlannerQuestionEvent,
    PlannerStatusEvent,
    PlannerTurnEvent,
    ResearchPlanResponse,
)
from llama_index.llms.openai import OpenAI

from .llm import get_planner_llm_resource
from .schemas import PlannerAgentOutput, ResearchPlan, ResearchPlanState

logger = logging.getLogger(__name__)


class DeepResearchPlanWorkflow(Workflow):
    """Deep Research planning workflow (HITL conversation + persistence).

    - config loaded via ResourceConfig
    - cloud client injected via Resource(get_llama_cloud_client)
    - idempotent Agent Data storage

    NOTE: The FunctionAgent integration is implemented as a pure callable
    inside `_run_planner_agent()`. In your target app, replace this stub with
    your `AgentFactoryService.build_agent(...).run(...)` wiring.
    """

    async def _run_planner_agent(
        self,
        *,
        llm: OpenAI,
        state: ResearchPlanState,
        user_message: str,
    ) -> PlannerAgentOutput:
        """Run the planning agent for a single turn.

        This workflow is the orchestration shell. The "agent" here is intentionally
        minimal and designed to be replaced by your real FunctionAgent.

        The key thing we want to demonstrate is how an LLM client is injected as a
        workflow Resource so we can iterate on planning logic without changing
        step orchestration.
        """

        if not state.plan.outline:
            expanded_query = await llm.apredict(
                "Rewrite this user query into a single, expanded search query.\n"
                "User query: {initial_query}",
                initial_query=state.initial_query or user_message,
            )
            plan = ResearchPlan(
                clarifying_questions=[],
                expanded_queries=[expanded_query],
                outline=["Overview", "Key trade-offs", "Recommendations", "Sources"],
                assumptions=[],
            )
            return PlannerAgentOutput(kind="plan", plan=plan)

        follow_up = await llm.apredict(
            "Ask one concise clarifying question to improve this research plan.",
            user_message=user_message,
        )
        return PlannerAgentOutput(kind="question", question=follow_up)

    async def _persist_session(
        self,
        *,
        llama_cloud_client: AsyncLlamaCloud,
        research_config: ResearchConfig,
        state: ResearchPlanState,
    ) -> str:
        """Persist the session record idempotently and return agent_data item id."""

        if state.research_id is None:
            raise ValueError("research_id must be set before persistence")

        record = {
            "research_id": state.research_id,
            "status": state.status,
            "initial_query": state.initial_query,
            "plan": state.plan.model_dump(),
        }

        # delete/replace by stable id
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
    async def process_turn(
        self,
        ctx: Context[ResearchPlanState],
        ev: StartEvent | PlannerTurnEvent,
        llama_cloud_client: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        planner_llm: Annotated[OpenAI, Resource(get_planner_llm_resource)],
        research_config: Annotated[
            ResearchConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="research",
                label="Research Config",
                description="Deep research collection + settings",
            ),
        ],
    ) -> ResearchPlanResponse | PlannerQuestionEvent:
        """Process a user turn and either ask a follow-up or finish with a plan."""

        if isinstance(ev, StartEvent):
            # Handle both PlanStartEvent and generic StartEvent (with data payload)
            user_message = getattr(ev, "initial_query", None) or ev.get("initial_query")
            if not user_message:
                raise ValueError("StartEvent received but missing 'initial_query'")

            async with ctx.store.edit_state() as state:
                state.initial_query = user_message
                # stable id - keep simple for template; real impl likely uses UUID.
                state.research_id = (
                    state.research_id
                    or f"research-{hashlib.sha256(user_message.encode('utf-8')).hexdigest()[:10]}"
                )
                state.status = "planning"
        else:
            user_message = ev.message

        ctx.write_event_to_stream(
            PlannerStatusEvent(level="info", message="Thinking")
        )

        try:
            state = await ctx.store.get_state()
            output = await self._run_planner_agent(
                llm=planner_llm,
                state=state,
                user_message=user_message,
            )
        except Exception as e:
            logger.error("Planning agent failed", exc_info=True)
            ctx.write_event_to_stream(
                PlannerStatusEvent(level="error", message=f"Planning failed: {e}")
            )
            raise

        if output.kind == "question":
            question = output.question or "Can you clarify your goal?"
            async with ctx.store.edit_state() as state:
                state.last_question = question
            ctx.write_event_to_stream(PlannerQuestionEvent(question=question))
            return PlannerQuestionEvent(question=question)

        if output.plan is None:
            raise ValueError("Planner returned kind='plan' but no plan payload")

        async with ctx.store.edit_state() as state:
            state.plan = output.plan
            state.status = "awaiting_approval"

        ctx.write_event_to_stream(
            PlannerFinalPlanEvent(
                plan=(await ctx.store.get_state()).plan.model_dump()
            )
        )

        try:
            item_id = await self._persist_session(
                llama_cloud_client=llama_cloud_client,
                research_config=research_config,
                state=await ctx.store.get_state(),
            )
        except Exception as e:
            logger.error("Persisting plan failed", exc_info=True)
            ctx.write_event_to_stream(
                PlannerStatusEvent(
                    level="error", message=f"Failed to save plan snapshot: {e}"
                )
            )
            raise
        ctx.write_event_to_stream(
            PlannerStatusEvent(
                level="info",
                message=f"Plan saved (agent_data_id={item_id}). Awaiting approval.",
            )
        )

        final_state = await ctx.store.get_state()
        if final_state.research_id is None:
            raise ValueError("research_id missing")

        return ResearchPlanResponse(
            research_id=final_state.research_id,
            status="awaiting_approval",
            plan=final_state.plan.model_dump(),
            agent_data_id=item_id,
        )

    @step
    async def ask_question(
        self, ctx: Context[ResearchPlanState], ev: PlannerQuestionEvent
    ) -> PlannerTurnEvent:
        # This uses the built-in HITL event types expected by the workflow server.
        response_event: HumanResponseEvent = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=ev.question,
            waiter_event=InputRequiredEvent(prefix=ev.question),
        )
        return PlannerTurnEvent(message=response_event.response)


workflow = DeepResearchPlanWorkflow(timeout=None)
