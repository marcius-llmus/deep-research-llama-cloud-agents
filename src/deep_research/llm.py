from typing import Annotated
from llama_index.core.llms import LLM
from llama_index.llms.google_genai import GoogleGenAI
from workflows.resource import ResourceConfig

from .config import ResearchConfig

def get_planner_llm_resource(
    research_config: Annotated[
        ResearchConfig,
        ResourceConfig(
            config_file="configs/config.json",
            path_selector="research",
            label="Research Config",
            description="Deep research collection + settings",
        ),
    ],
) -> LLM:
    """Resource factory for the planning LLM client.

    Uses a Google GenAI client configured via ResearchConfig.
    """

    llm_cfg = research_config.planner.main_llm
    return GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)
