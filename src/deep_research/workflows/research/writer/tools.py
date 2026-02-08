from __future__ import annotations

from typing import Annotated

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from workflows import Context
from pydantic import Field

from deep_research.config import ResearchConfig
from deep_research.services.file_service import read_text_file, write_text_file
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
        "update_report",
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

    async def update_report(
        self,
        ctx: Context,
        patch: Annotated[
            str,
            Field(
                description=(
                    "MOCK patch text to apply to the report file referenced by workflow state `report.path`."
                )
            ),
        ],
    ) -> str:
        state = await ctx.store.get_state()
        report_path = state[StateNamespace.REPORT][ReportStateKey.PATH]

        original = read_text_file(report_path)
        updated = self.report_patch_service.apply_patch_mock(
            original_text=original,
            patch_text=patch,
        )
        write_text_file(report_path, updated)
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


def get_writer_tools(*, config: ResearchConfig | None = None) -> list:
    cfg = config or ResearchConfig()
    tools_spec = WriterTools(config=cfg)
    return tools_spec.to_tool_list()
