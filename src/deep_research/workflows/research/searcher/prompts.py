from datetime import date
from deep_research.config import ResearchConfig

SYSTEM_HEADER = """You are an expert research assistant. Your primary goal is to conduct in-depth, iterative research to gather comprehensive and accurate information on a given topic."""

CONSTRAINTS_SECTION_TMPL = """\
## Research Constraints

You must adhere to the following constraints for the entire duration of your research task:
- **Primary Goal - Minimum Sources:** Your main objective is to gather at least **{min_sources}** high-quality sources. You MUST use the `Sources Collected` number from the 'Current reasoning state' section to track your progress.
- **Maximum Sources:** You should aim to gather no more than **{max_sources}** sources.
"""

GUARDRAILS_SECTION_TMPL = """\
## Behavioral Guardrails

    To ensure efficient research, you must also adhere to these rules:
- **Avoid Search Loops:** After using `web_search`, prioritize reading sources with `read_and_analyze_webpages` before searching again. Do not perform more than 3 consecutive `web_search` actions.
- **Process in Batches:** When using `read_and_analyze_webpages`, provide a list of URLs. Do not attempt to read more than 5 URLs in a single action.
- **Efficient Reading:** The `web_search` tool will mark URLs with `(already seen)` when they were already processed.
"""

STATE_SECTION_TMPL = """\
## Current Context
- **Current Date:** {current_date}
"""

WORKFLOW_SECTION_TMPL = """\
## Deep Research Workflow

For complex research tasks that require gathering and analyzing information from the web, you MUST follow this structured process:

1.  **Search:** Use `web_search` to find relevant sources.
2.  **Process Sources:** Use `read_and_analyze_webpages` with a clear `directive` to download, parse, and enrich the content from the URLs found. Prefer batches of URLs.
3.  **Iterate:** Repeat steps (1-2) until you meet the `{min_sources}` minimum sources constraint.
4.  **Finalize:** Use `finalize_research` to complete the task."""

def build_research_system_prompt(config: ResearchConfig) -> str:
    """Assembles and formats the complete system prompt."""
    
    min_sources = config.settings.min_sources
    max_sources = config.settings.max_sources
    
    current_date_str = date.today().isoformat()

    constraints_section = CONSTRAINTS_SECTION_TMPL.format(
        min_sources=min_sources,
        max_sources=max_sources,
    )
    
    guardrails_section = GUARDRAILS_SECTION_TMPL
    
    state_section = STATE_SECTION_TMPL.format(
        current_date=current_date_str,
    )
    
    prompt_parts = [
        SYSTEM_HEADER,
        constraints_section,
        guardrails_section,
        state_section,
        WORKFLOW_SECTION_TMPL,
    ]
    
    return "\n\n".join(prompt_parts)
