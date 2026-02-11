from typing import Annotated

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.core.tools import ToolMetadata
from workflows import Context
from pydantic import BaseModel, Field, create_model

from deep_research.config import ResearchConfig
from deep_research.services.report_patch_service import ReportPatchService
from deep_research.workflows.research.reviewer.agent import workflow as reviewer_agent
from deep_research.workflows.research.state_keys import (
    ReportStateKey,
    StateNamespace,
)

from apply_patch_py.utils import (
    get_patch_format_instructions,
    get_patch_format_tool_instructions,
)


def _build_apply_patch_metadata() -> ToolMetadata:
    tool_description = get_patch_format_tool_instructions()
    diff_description = get_patch_format_instructions()

    schema: type[BaseModel] = create_model(
        "ApplyPatchToolSchema",
        diff=(str, Field(description=diff_description)),
    )

    return ToolMetadata(
        name="apply_patch",
        description=tool_description,
        fn_schema=schema,
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
        diff: str,
    ) -> str:
        updated = await self.report_patch_service.apply_patch(ctx=ctx, patch_text=diff)

        async with ctx.store.edit_state() as st:
            st[StateNamespace.REPORT][ReportStateKey.CONTENT] = updated

        return updated

    def to_tool_list(self, *args, **kwargs):
        metadata = _build_apply_patch_metadata()
        return super().to_tool_list(
            *args,
            **kwargs,
            func_to_metadata_mapping={"apply_patch": metadata},
        )

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
