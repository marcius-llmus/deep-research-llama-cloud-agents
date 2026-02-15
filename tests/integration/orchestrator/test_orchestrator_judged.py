import json

import pytest
from pydantic import BaseModel, Field
from llama_index.core import PromptTemplate

from deep_research.workflows.research.state import DeepResearchState
from deep_research.workflows.research.orchestrator import tools as orchestrator_tools
from deep_research.workflows.research.state import ResearchStateAccessor
from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem
from deep_research.workflows.research.orchestrator import agent as orchestrator_agent_module
from deep_research.workflows.research.orchestrator import agent as orchestrator_agent_module


class OrchestratorJudgeVerdict(BaseModel):
    tool_use_score: int = Field(..., ge=0, le=10)
    plan_adherence_score: int = Field(..., ge=0, le=10)
    workflow_score: int = Field(..., ge=0, le=10)
    passed: bool
    reasoning: str


ORCHESTRATOR_JUDGE_PROMPT = """
You are a strict QA auditor evaluating an Orchestrator agent that manages a research workflow.

The Orchestrator has ONLY two tools available:
- call_research_agent(prompt: str)
- call_write_agent(instruction: str)

The Orchestrator's job:
1) Follow the Research Plan step-by-step.
2) Use call_research_agent to gather evidence when needed.
3) Use call_write_agent when evidence is sufficient to update the report.
4) Repeat until the plan is satisfied.

You must output a JSON verdict.

Evaluation criteria:
1) Tool Use Correctness (Critical):
   - Did it call call_research_agent when evidence was needed?
   - Did it call call_write_agent after evidence was present?
   - Did it avoid redundant tool calls?

2) Plan Adherence:
   - Did it prioritize upstream dependencies?
   - Did it cover the plan requirements in a logical order?

3) Workflow Outcome:
   - Is the final report non-empty and plausibly satisfies the plan (given mocked tools)?
   - Did it stop in a reasonable place (not endless looping)?

Verdict schema:
{
  "tool_use_score": (0-10),
  "plan_adherence_score": (0-10),
  "workflow_score": (0-10),
  "passed": (boolean),
  "reasoning": "Short explanation of failures or success."
}

Inputs:

<Research Plan>
{research_plan}
</Research Plan>

<Initial Report>
{initial_report}
</Initial Report>

<Tool Events (ordered)>
{tool_events}
</Tool Events>

<Final Report>
{final_report}
</Final Report>
"""


@pytest.mark.asyncio
async def test_orchestrator_judged_happy_path(
    run_orchestrator,
    judge_llm,
    monkeypatch,
    batteries_research_plan,
    empty_research_state_dict,
):
    research_plan = batteries_research_plan
    initial_state = empty_research_state_dict

    async def _mock_call_research_agent(ctx, prompt: str) -> str:
        evidence = EvidenceBundle(
            items=[
                EvidenceItem(
                    url="https://tech-example.com/solid-state",
                    title="solid-state",
                    summary="Solid-state batteries use a solid electrolyte instead of a liquid one; potential higher energy density and improved safety; manufacturing costs high; dendrite formation challenges.",
                    content="Solid-state batteries use a solid electrolyte instead of a liquid one. Higher energy density (up to 500 Wh/kg). Less flammable. Costs high; dendrite formation remains a hurdle.",
                    metadata={"world": "batteries"},
                    assets=[],
                ),
                EvidenceItem(
                    url="https://energy-example.com/li-ion",
                    title="li-ion",
                    summary="Li-ion batteries use liquid electrolytes; mature and cheaper to manufacture; thermal runaway risk; lower theoretical energy density (~250 Wh/kg).",
                    content="Li-ion batteries use liquid electrolytes. Mature and cheap ($130/kWh). Thermal runaway risks. Theoretical energy density limit ~250 Wh/kg.",
                    metadata={"world": "batteries"},
                    assets=[],
                ),
                EvidenceItem(
                    url="https://safety-example.org/battery-safety",
                    title="battery-safety",
                    summary="Liquid electrolytes can catch fire at ~60C; solid electrolytes stable to 200C+.",
                    content="Liquid electrolytes can catch fire at 60C. Solid electrolytes are stable up to 200C+.",
                    metadata={"world": "batteries"},
                    assets=[],
                ),
            ]
        )

        async with ResearchStateAccessor.edit(ctx) as state:
            state.research_turn.evidence = evidence
            state.research_turn.add_seen_urls([i.url for i in evidence.items])

        return evidence.get_summary()

    async def _mock_call_write_agent(ctx, instruction: str) -> str:
        async with ResearchStateAccessor.edit(ctx) as state:
            state.research_artifact.content = (
                "# Solid-State vs Lithium-Ion Batteries\n\n"
                "## Definitions and Working Principles\n"
                "- **Solid-state batteries (SSB):** Use a **solid electrolyte** instead of a liquid electrolyte.\n"
                "- **Lithium-ion (Li-ion):** Use a **liquid electrolyte** to move ions between electrodes; commercially mature.\n\n"
                "## Comparison: Energy Density and Safety\n"
                "- **Energy density:** Evidence suggests SSB can reach **up to ~500 Wh/kg** while Li-ion is around **~250 Wh/kg**.\n"
                "- **Safety / thermal stability:** Liquid electrolytes can catch fire at **~60°C**, while solid electrolytes are stable to **200°C+**.\n\n"
                "## Manufacturing Cost / Scale Challenges\n"
                "- SSB manufacturing costs are described as high and dendrite formation remains a technical hurdle.\n\n"
                "## Trade-off Summary\n"
                "SSB promise higher energy density and improved safety, but face cost and materials/engineering challenges; Li-ion is mature and cost-effective today.\n\n"
                "## Sources\n"
                "- https://tech-example.com/solid-state\n"
                "- https://energy-example.com/li-ion\n"
                "- https://safety-example.org/battery-safety\n"
            )

            state.research_turn.clear()

        return "Writing session finished. Report updated."

    monkeypatch.setattr(orchestrator_agent_module, "call_research_agent", _mock_call_research_agent)
    monkeypatch.setattr(orchestrator_agent_module, "call_write_agent", _mock_call_write_agent)

    state, events, result, trace_path = await run_orchestrator(
        user_msg=research_plan,
        initial_state=initial_state,
        trace_name="orchestrator_judged_happy_path",
    )

    state_obj = DeepResearchState.model_validate(state.model_dump())
    final_report = state_obj.research_artifact.content
    assert "Solid-State" in final_report
    assert "Sources" in final_report

    tool_calls = [e for e in events if e.type == "ToolCall"]
    tool_names = [e.tool_name for e in tool_calls]
    assert "call_research_agent" in tool_names
    assert "call_write_agent" in tool_names

    tool_events_str = json.dumps([e.__dict__ for e in events], indent=2, default=str)
    prompt = PromptTemplate(template=ORCHESTRATOR_JUDGE_PROMPT)
    verdict = await judge_llm.astructured_predict(
        OrchestratorJudgeVerdict,
        prompt=prompt,
        research_plan=research_plan,
        initial_report="",
        tool_events=tool_events_str,
        final_report=final_report,
    )

    print(f"\nJudge Verdict: {verdict.model_dump_json(indent=2)}")
    assert verdict.passed, f"Orchestrator failed judge check: {verdict.reasoning}"
    assert verdict.tool_use_score >= 7
    assert verdict.plan_adherence_score >= 7
    assert verdict.workflow_score >= 7
