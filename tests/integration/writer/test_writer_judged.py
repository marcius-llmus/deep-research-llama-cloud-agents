import pytest
from pydantic import BaseModel, Field
from llama_index.core import PromptTemplate

from deep_research.services.report_patch_service import ReportPatchService
from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem
from deep_research.workflows.research.state import DeepResearchState, ResearchArtifactState, ResearchTurnState


class WriterTurnJudgeVerdict(BaseModel):
    grounding_score: int = Field(..., ge=0, le=10)
    instruction_score: int = Field(..., ge=0, le=10)
    integrity_score: int = Field(..., ge=0, le=10)
    passed: bool
    reasoning: str


WRITER_TURN_JUDGE_PROMPT = """
You are a strict Editor-in-Chief auditing a technical writer's work turn-by-turn.

The writer updates a markdown report iteratively via patches.

For the CURRENT TURN, evaluate the NEW report state after applying the patch.

Rules:
1) Grounding (critical): The NEW report must only introduce factual claims present in <Research Notes>.
2) Instruction adherence: The NEW report must move toward satisfying <Instruction>.
3) Integrity: The NEW report must preserve valid content from <Previous Report> unless the instruction requires changing it.
4) Patch sanity: The patch should be consistent with the NEW report (i.e., the changes described by the patch are reflected).

Output a JSON verdict.

Verdict schema:
{
  "grounding_score": (0-10),
  "instruction_score": (0-10),
  "integrity_score": (0-10),
  "passed": (boolean),
  "reasoning": "Short explanation."
}

Inputs:

<Instruction>
{instruction}
</Instruction>

<Research Notes>
{research_notes}
</Research Notes>

<Previous Report>
{previous_report}
</Previous Report>

<Patch>
{patch}
</Patch>

<New Report>
{new_report}
</New Report>
"""


@pytest.mark.asyncio
async def test_writer_turnwise_judged_from_single_orchestrator_instruction(run_writer, judge_llm):
    instruction = (
        "Add a section \"2. Energy Density and Safety Comparison\" to the report.\n"
        "- Compare energy density: Li-ion (~250 Wh/kg) vs. SSBs (potential for higher density, mention ~500 Wh/kg if available).\n"
        "- Compare safety: Li-ion liquid electrolytes (flammable, thermal runaway risk at ~60C) vs. SSB solid electrolytes (stable to 200C+, non-flammable).\n"
        "- Cite https://energy-example.com/li-ion and https://safety-example.org/battery-safety."
    )

    # NOTE: We add extra newlines at the end to ensure the agent has a clear "append target"
    # and doesn't struggle with EOF context matching.
    original_report = (
        "# Comparative Analysis: Solid-State vs. Lithium-Ion Batteries\n\n"
        "## 1. Definitions and Mechanisms\n"
        "- **Lithium-Ion (Li-ion) batteries:** Use a liquid electrolyte to move ions between electrodes; commercially mature.\n"
        "- **Solid-State Batteries (SSBs):** Replace the liquid electrolyte with a solid material.\n"
        "- **Sources:** https://tech-example.com/solid-state, https://energy-example.com/li-ion\n\n"
    )

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

    initial_state = DeepResearchState(
        research_artifact=ResearchArtifactState(content=original_report),
        research_turn=ResearchTurnState(evidence=evidence),
    ).model_dump()

    writer_user_msg = f"Instruction: {instruction}"
    state, events, _result, _trace_path = await run_writer(
        user_msg=writer_user_msg,
        initial_state=initial_state,
        trace_name="writer_turnwise_judged",
    )

    patch_tool_calls = [
        e for e in events if e.type == "ToolCall" and e.tool_name == "apply_patch" and isinstance(e.tool_kwargs, dict)
    ]
    assert patch_tool_calls, "Writer did not call apply_patch; cannot judge turnwise."

    patch_service = ReportPatchService()
    research_notes = evidence.get_content_for_writing()

    previous_report = original_report
    prompt = PromptTemplate(template=WRITER_TURN_JUDGE_PROMPT)

    for idx, call in enumerate(patch_tool_calls, start=1):
        patch_text = str(call.tool_kwargs.get("diff") or "")

        # We apply the patch locally to verify it works and to get the new state for the judge
        try:
            new_report, _added, _removed = await patch_service.apply_patch(
                original_text=previous_report,
                patch_text=patch_text,
            )
        except Exception as e:
            pytest.fail(f"Patch application failed at turn {idx}: {e}")

        verdict = await judge_llm.astructured_predict(
            WriterTurnJudgeVerdict,
            prompt=prompt,
            instruction=instruction,
            research_notes=research_notes,
            previous_report=previous_report,
            patch=patch_text,
            new_report=new_report,
        )

        print(f"\\nTurn {idx} Verdict: {verdict.model_dump_json(indent=2)}")
        assert verdict.passed, f"Writer failed at patch turn {idx}: {verdict.reasoning}"
        assert verdict.grounding_score >= 8
        assert verdict.instruction_score >= 8
        assert verdict.integrity_score >= 8

        previous_report = new_report

    assert "Energy Density" in state.research_artifact.content or "Energy density" in state.research_artifact.content
