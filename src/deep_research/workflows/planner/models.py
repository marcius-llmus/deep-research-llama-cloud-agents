from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TextSynthesizerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    synthesis_type: str = Field(
        default="report",
        description=(
            "The intended output type. Free-form string. Examples: Report, Blog post, Email, Tweet, Technical paper."
        ),
    )
    tone: str = Field(
        default="objective",
        description=(
            "Overall tone guideline. Free-form string. Examples: Objective, Formal, Humorous, Conversational, Noir."
        ),
    )
    point_of_view: str = Field(
        default="third_person",
        description=(
            "Point of view guideline. Free-form string. Examples: First person, Second person, Third person."
        ),
    )
    language: str = Field(
        default="english",
        description=(
            "Output language guideline. Free-form string. Examples: English, Spanish, French. Can be any value."
        ),
    )
    target_audience: str = Field(
        default="general_audience",
        description=(
            "Intended audience guideline. Free-form string. Examples: General audience, Beginners, Students, Business, Technical experts."
        ),
    )
    target_words: int | None = Field(
        default=4000,
        ge=1,
        le=100_000,
        description=(
            "Approximate target total word count for the final output. Guide, not a strict requirement."
        ),
    )
    output_format: str = Field(
        default="markdown",
        description=(
            "Output format guideline. Free-form string. Examples: Markdown, Plaintext."
        ),
    )
    custom_instructions: str = Field(
        default="",
        description=(
            "Free-form extra requirements not captured by other fields. Use for mixed tone, section-specific style, "
            "Do/don't lists, special formatting rules, etc."
        ),
    )


class PlannerAgentOutput(BaseModel):
    """Structured output contract for the planning agent per turn."""

    decision: Literal["propose_plan", "finalize"]
    response: str = Field(description="The message to show to the user (question or plan explanation).")
    plan: str = Field(
        description=(
            "The current research plan as raw text. Always required."
        ),
    )
    text_config: TextSynthesizerConfig = Field(
        default_factory=TextSynthesizerConfig,
        description="Output configuration guidelines for downstream agents. Values are free-form strings.",
    )


class ResearchPlanState(BaseModel):
    initial_query: str | None = None
    research_id: str | None = None
    plan_text: str | None = None
    text_config: TextSynthesizerConfig = Field(default_factory=TextSynthesizerConfig)
    status: Literal["planning", "finalized", "failed"] = "planning"
