from deep_research.workflows.planner.models import TextSynthesizerConfig


def format_text_config(
    text_config: TextSynthesizerConfig | dict | None,
    *,
    with_examples: bool = False,
) -> str:
    cfg = TextSynthesizerConfig.model_validate(text_config)

    examples: dict[str, str] = {
        "synthesis_type": "Report, Blog post, Email, Tweet, Technical paper",
        "tone": "Objective, Formal, Humorous, Conversational",
        "point_of_view": "First person, Second person, Third person",
        "language": "English, Spanish, French",
        "target_audience": "General audience, Beginners, Students, Technical experts",
        "output_format": "Markdown, Plaintext",
        "custom_instructions": "Do/don't lists, Special formatting rules, Section-specific requirements",
    }

    def _format_value(label: str, value: str) -> str:
        if with_examples and label in examples:
            return f"{value} ({examples[label]})".strip()
        return value

    lines = [
        "========================",
        "OUTPUT CONFIG (GUIDE)",
        "========================",
        f"- synthesis_type: {_format_value('synthesis_type', cfg.synthesis_type)}",
        f"- tone: {_format_value('tone', cfg.tone)}",
        f"- point_of_view: {_format_value('point_of_view', cfg.point_of_view)}",
        f"- language: {_format_value('language', cfg.language)}",
        f"- target_audience: {_format_value('target_audience', cfg.target_audience)}",
        f"- target_words: {cfg.target_words}",
        f"- output_format: {_format_value('output_format', cfg.output_format)}",
    ]

    if cfg.custom_instructions.strip():
        lines.append(
            f"- custom_instructions: {_format_value('custom_instructions', cfg.custom_instructions.strip())}"
        )

    return "\n".join(lines)
