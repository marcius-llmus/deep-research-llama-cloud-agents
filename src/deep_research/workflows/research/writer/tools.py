from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.core.tools import ToolMetadata
from workflows import Context
from pydantic import BaseModel, Field, create_model

from deep_research.config import ResearchConfig
from deep_research.services.report_patch_service import ReportPatchService
from deep_research.workflows.research.state import ResearchStateAccessor

from deep_research.services.patch_prompts import (
    get_patch_format_instructions,
    get_patch_format_tool_instructions,
)
from deep_research.workflows.research.writer.models import ReviewPatchResponse


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
        ctx: Context,
        diff: str,
    ) -> str:
        state = await ResearchStateAccessor.get(ctx)
        
        current_draft = state.research_artifact.turn_draft
        if current_draft is None:
            current_draft = state.research_artifact.content

        new_content, added, removed = await self.report_patch_service.apply_patch(
            original_text=current_draft,
            patch_text=diff,
        )

        async with ResearchStateAccessor.edit(ctx) as edit_state:
            if edit_state.research_artifact.turn_draft is None:
                edit_state.research_artifact.turn_draft = current_draft
            edit_state.research_artifact.pending_patch_content = new_content

        return (
            f"Patch applied to buffer. Added {added} lines, removed {removed} lines. "
            "Please call review_patch to commit this change to the draft."
        )

    async def review_patch(self, ctx: Context) -> str: # noqa
        async with ResearchStateAccessor.edit(ctx) as state:
            pending = state.research_artifact.pending_patch_content
            current_draft = state.research_artifact.turn_draft

            if pending is None:
                return ReviewPatchResponse(
                    decision="rejected",
                    message="No pending patch to review. Please apply a patch first.",
                ).model_dump_json()


            # todo: maybe we can improve it later
            if current_draft and len(current_draft) > 100 and len(pending) < len(current_draft) * 0.5:
                state.research_artifact.pending_patch_content = None
                return ReviewPatchResponse(
                    decision="rejected",
                    message="Patch rejected: Deletes more than 50% of the report content. Please try again.",
                ).model_dump_json()

            added, removed = self.report_patch_service.count_line_changes(
                old=current_draft, new=pending
            )

            state.research_artifact.turn_draft = pending
            state.research_artifact.pending_patch_content = None

        return ReviewPatchResponse(
            decision="approved",
            message="Patch reviewed and committed to draft. You may continue applying patches or call finish_writing.",
            added_lines=added,
            removed_lines=removed,
        ).model_dump_json()

    async def finish_writing(self, ctx: Context) -> str: # noqa
        """
        Finalizes the writing session. Commits the current draft to the main report and stops the writer agent.
        """
        async with ResearchStateAccessor.edit(ctx) as state:
            draft = state.research_artifact.turn_draft
            
            if draft is None:
                return "No changes were made in this session."

            state.research_artifact.content = draft
            state.research_artifact.turn_draft = None
            state.research_artifact.pending_patch_content = None
            
            state.research_turn.clear()

        return "Writing session finished. Report updated."

    def to_tool_list(self, *args, **kwargs):
        apply_patch_metadata = _build_apply_patch_metadata()
        return super().to_tool_list(
            *args,
            **kwargs,
            func_to_metadata_mapping={
                "apply_patch": apply_patch_metadata,
            },
        )
