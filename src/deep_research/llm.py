from typing import Annotated
import os

from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
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

    Uses an OpenAI client configured via ResearchConfig.
    """

    llm_cfg = research_config.llm
    if llm_cfg.provider == "openai":
        return OpenAI(
            model=llm_cfg.model,
            temperature=llm_cfg.temperature,
            reasoning_effort=llm_cfg.reasoning_effort,
        )
    elif llm_cfg.provider == "gemini":
        from llama_index.llms.google_genai import GoogleGenAI
        return GoogleGenAI(model=llm_cfg.model, temperature=llm_cfg.temperature)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {llm_cfg.provider!r}. Expected: 'openai' or 'gemini'."
        )
