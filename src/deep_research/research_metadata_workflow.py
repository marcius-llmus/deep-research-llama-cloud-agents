from typing import Annotated

import jsonref
from workflows import Workflow, step
from workflows.events import StartEvent
from workflows.resource import ResourceConfig

from .config import ResearchConfig
from .events import ResearchMetadataResponse


class ResearchMetadataWorkflow(Workflow):
    """Provide Deep Research runtime metadata to the UI."""

    @step
    async def get_metadata(
        self,
        _: StartEvent,
        research_config: Annotated[
            ResearchConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="research",
                label="Research Config",
                description="Deep research collection + settings",
            ),
        ],
    ) -> ResearchMetadataResponse:
        settings_schema = research_config.settings.model_json_schema()
        # Keep consistent with existing metadata workflow: resolve $refs.
        settings_schema = jsonref.replace_refs(settings_schema, proxies=False)
        return ResearchMetadataResponse(
            research_collection=research_config.collections.research_collection,
            research_settings_schema=settings_schema,
        )


workflow = ResearchMetadataWorkflow(timeout=None)
