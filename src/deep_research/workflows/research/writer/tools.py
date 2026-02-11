from typing import Annotated, Literal

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.core.tools import ToolMetadata
from workflows import Context
from pydantic import BaseModel, Field, create_model

from deep_research.config import ResearchConfig
from deep_research.services.report_patch_service import ReportPatchService
from deep_research.workflows.research.state import DeepResearchState

from deep_research.services.patch_prompts import (
    get_patch_format_instructions,
    get_patch_format_tool_instructions,
)


class ReviewPatchResponse(BaseModel):
    decision: Literal["approved", "rejected"] = Field(description="approved or rejected")
    message: str
    added_lines: int = 0
    removed_lines: int = 0


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


def _build_review_patch_metadata() -> ToolMetadata:
    schema: type[BaseModel] = create_model("ReviewPatchToolSchema")

    return ToolMetadata(
        name="review_patch",
        description=(
            "Reviews the pending draft report. If structurally valid, commits the draft to the main report and clears the draft. "
            "Returns a structured JSON result with approval/rejection and line counts."
        ),
        fn_schema=schema,
    )


def _count_line_changes(*, old: str, new: str) -> tuple[int, int]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    old_set = {}
    for line in old_lines:
        old_set[line] = old_set.get(line, 0) + 1

    additions = 0
    for line in new_lines:
        if old_set.get(line, 0) > 0:
            old_set[line] -= 1
            continue
        additions += 1

    deletions = sum(max(0, v) for v in old_set.values())
    return additions, deletions


class WriterTools(BaseToolSpec):
    spec_functions = [
        "apply_patch",
        "review_patch",
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
        ctx: Context[DeepResearchState],
        diff: str,
    ) -> str:
        state: DeepResearchState = await ctx.store.get_state()
        current = state.research_artifact.content

        new_content, added, removed = await self.report_patch_service.apply_patch(
            original_text=current,
            patch_text=diff,
        )

        async with ctx.store.edit_state() as edit_state:
            edit_state.research_artifact.draft_content = new_content

        return (
            f"Report patched. Added {added} lines, removed {removed} lines. Waiting for review."
        )

    async def review_patch(self, ctx: Context[DeepResearchState]) -> str: # noqa
        async with ctx.store.edit_state() as state:
            draft = state.research_artifact.draft_content
            current = state.research_artifact.content

            if not draft.strip():
                return ReviewPatchResponse(
                    decision="rejected",
                    message="Draft content is empty. Please apply a patch first.",
                ).model_dump_json()

            added, removed = _count_line_changes(old=current, new=draft)

            state.research_artifact.content = draft
            state.research_artifact.draft_content = ""
            state.research_turn.clear()

        return ReviewPatchResponse(
            decision="approved",
            message="Patch reviewed and committed. Report updated. New research turn started.",
            added_lines=added,
            removed_lines=removed,
        ).model_dump_json()

    def to_tool_list(self, *args, **kwargs):
        apply_patch_metadata = _build_apply_patch_metadata()
        review_patch_metadata = _build_review_patch_metadata()
        return super().to_tool_list(
            *args,
            **kwargs,
            func_to_metadata_mapping={
                "apply_patch": apply_patch_metadata,
                "review_patch": review_patch_metadata,
            },
        )

    
