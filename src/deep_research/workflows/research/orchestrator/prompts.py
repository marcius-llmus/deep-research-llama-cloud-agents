from deep_research.workflows.research.searcher.models import EvidenceBundle
from deep_research.workflows.research.state_keys import ReportStateKey, ResearchStateKey, StateNamespace

ORCHESTRATOR_SYSTEM_TEMPLATE = """
You are the Chief Editor and Orchestrator of a deep research project.
Your goal is to produce a comprehensive report by coordinating a Researcher (who finds info) and a Writer (who compiles it).

### Current Report Status
{report_status}

### Pending Evidence (Summaries)
The following evidence has been gathered but not yet incorporated into the report:
{pending_evidence}

### Instructions
1. Analyze the "Pending Evidence". Does it cover the current gaps in the report?
2. Compare it against the "Current Report Status".
3. Decide your next move:
   - If you need more information, instruct the **SearcherAgent** to find it. Be specific about what is missing.
   - If the evidence is sufficient for a section, instruct the **WriterAgent** to write/update that section using the pending evidence.
   - If the report is complete, run the **ReviewerAgent**.

Keep your instructions clear and directive.
"""

def build_orchestrator_system_prompt(state: dict) -> str:
    """
    Constructs the dynamic system prompt for the Orchestrator.
    Injects the current report status and summaries of pending evidence.
    """
    
    report_state = state.get(StateNamespace.REPORT, {})
    report_content = report_state.get(ReportStateKey.CONTENT, "")
    if not report_content:
        report_status = "(The report is currently empty.)"
    else:
        preview_len = 2000
        if len(report_content) > preview_len:
            report_status = f"{report_content[:preview_len]}...\n(Report truncated, total length: {len(report_content)} chars)"
        else:
            report_status = report_content

    research_state = state.get(StateNamespace.RESEARCH, {})
    pending_raw = research_state.get(ResearchStateKey.PENDING_EVIDENCE, {})
    
    pending_evidence_str = "(No pending evidence.)"
    if pending_raw:
        try:
            bundle = EvidenceBundle.model_validate(pending_raw)
            pending_evidence_str = bundle.get_summary()
        except Exception:
            pending_evidence_str = "(Error parsing pending evidence state.)"

    return ORCHESTRATOR_SYSTEM_TEMPLATE.format(
        report_status=report_status,
        pending_evidence=pending_evidence_str
    )
