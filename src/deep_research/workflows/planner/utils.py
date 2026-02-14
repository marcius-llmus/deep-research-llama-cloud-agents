from deep_research.workflows.planner.models import TextSynthesizerConfig


def format_text_config(text_config: TextSynthesizerConfig | dict | None) -> str:
    cfg = TextSynthesizerConfig.model_validate(text_config)

    lines = [
        "========================",
        "OUTPUT CONFIG (GUIDE)",
        "========================",
        f"- synthesis_type: {cfg.synthesis_type}",
        f"- tone: {cfg.tone}",
        f"- point_of_view: {cfg.point_of_view}",
        f"- language: {cfg.language}",
        f"- target_audience: {cfg.target_audience}",
        f"- target_words: {cfg.target_words}",
        f"- output_format: {cfg.output_format}",
    ]

    if custom := cfg.custom_instructions.strip():
        lines.extend(["", "Custom instructions:", custom])

    return "\n".join(lines)
