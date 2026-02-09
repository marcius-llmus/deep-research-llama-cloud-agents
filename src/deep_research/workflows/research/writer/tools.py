from typing import Annotated

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from workflows import Context
from pydantic import Field

from deep_research.config import ResearchConfig
from deep_research.services.report_patch_service import ReportPatchService
from deep_research.workflows.research.reviewer.agent import workflow as reviewer_agent
from deep_research.workflows.research.state_keys import (
    ReportStateKey,
    ReportStatus,
    StateNamespace,
)


class WriterTools(BaseToolSpec):
    spec_functions = [
        "apply_patch",
        "finalize",
        "reviewer",
    ]

    def __init__(
        self,
        *,
        config: ResearchConfig,
        report_patch_service: ReportPatchService | None = None,
    ):
        self.config = config
        self.report_patch_service = report_patch_service or ReportPatchService()

    async def apply_patch(
        self,
        ctx: Context,
        diff: Annotated[
            str,
            Field(
                description=(
                    "Unified diff to apply to the report markdown stored in workflow state "
                    "under `report.content`."
                )
            ),
        ],
    ) -> str:
        state = await ctx.store.get_state()
        original = state[StateNamespace.REPORT][ReportStateKey.CONTENT]

        updated = self.report_patch_service.apply_patch_mock(
            original_text=original,
            patch_text=diff,
        )

        async with ctx.store.edit_state() as st:
            st[StateNamespace.REPORT][ReportStateKey.CONTENT] = updated

        return updated


    async def finalize(self, ctx: Context) -> str:
        async with ctx.store.edit_state() as state:
            state[StateNamespace.REPORT][ReportStateKey.STATUS] = ReportStatus.COMPLETED
        return "Finalized"

    async def reviewer(
        self,
        ctx: Context,
        report_markdown: Annotated[
            str,
            Field(description="Report markdown to review."),
        ],
    ) -> str:
        result = await reviewer_agent.run(
            user_msg=f"Review the following report:\n\n{report_markdown}",
            ctx=ctx,
        )
        return str(result.response)
