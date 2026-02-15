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
    ]

    def __init__(
        self,
        *,
        config: ResearchConfig,
    ):
        self.config = config
        self.report_patch_service = ReportPatchService()

    async def apply_patch(
        self,
        ctx: Context,
        diff: str,
    ) -> str:
        state = await ResearchStateAccessor.get(ctx)

        current_draft = state.research_artifact.turn_draft or state.research_artifact.content

        new_content, added, removed = await self.report_patch_service.apply_patch(
            original_text=current_draft,
            patch_text=diff,
        )

        if current_draft and len(current_draft) > 100 and len(new_content) < len(current_draft) * 0.5:
            raise ValueError(
                "Patch rejected: Deletes more than 50% of the report content. Please try again."
            )

        async with ResearchStateAccessor.edit(ctx) as edit_state:
            edit_state.research_artifact.turn_draft = new_content

        return f"Patch applied. Added {added} lines, removed {removed} lines."

    async def finish_writing(self, ctx: Context) -> str: # noqa
        """
        Finalizes the writing session. Commits the current draft to the main report and stops the writer agent.
        """
        async with ResearchStateAccessor.edit(ctx) as state:
            draft = state.research_artifact.turn_draft
            
            if draft is None:
                raise ValueError("draft should not be empty")

            # todo: not needed actually
            state.research_artifact.content = draft
            state.research_artifact.turn_draft = None
            
            state.research_turn.clear()

        return draft

    def to_tool_list(self, *args, **kwargs):
        apply_patch_metadata = _build_apply_patch_metadata()
        return super().to_tool_list(
            *args,
            **kwargs,
            func_to_metadata_mapping={
                "apply_patch": apply_patch_metadata,
            },
        )
