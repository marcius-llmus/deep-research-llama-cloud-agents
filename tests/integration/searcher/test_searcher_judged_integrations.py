import json

import pytest
from pydantic import BaseModel, Field
from llama_index.core import PromptTemplate


class SearcherJudgeVerdict(BaseModel):
    passed: bool = Field(..., description="Overall pass/fail")
    decomposition_ok: bool = Field(..., description="Query planning/decomposition aligns with goal intent")
    search_and_read_ok: bool = Field(..., description="Agent performed search and generated evidence")
    stopped_ok: bool = Field(..., description="Agent finalized without looping indefinitely")
    coverage_ok: bool = Field(
        ..., description="Evidence summaries are sufficient to answer the goal as asked (within this mock world)"
    )
    issues: list[str] = Field(default_factory=list)


JUDGE_PROMPT = """
You are judging an integration test run of a research agent.

You will be given:
- The user goal
- A tool trace (tool calls + key outputs)
- The final evidence summary (from state)

Your job is to decide if the run is correct.

Rules:
- Be strict about intent capture: the planned queries should match the goal and not add unrelated constraints.
- The agent must use web_search and then generate_evidences from discovered URLs.
- The agent must stop by calling finalize_research.
- Coverage: If the mock evidence contains enough info to answer the goal, coverage_ok should be true.
  If the goal asks for things not present in the mock world (e.g., Tokyo seasonal weather but no weather pages exist),
  then coverage_ok should be false but the run can still pass overall if the agent stopped correctly and reported limitations.

Return a structured JSON matching SearcherJudgeVerdict.

GOAL:
{goal}

TRACE (JSON):
{trace_json}

EVIDENCE SUMMARY:
{evidence_summary}
"""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "goal,trace_name",
    [
        (
            "latest doj news",
            "judge_latest_doj",
        ),
        (
            "site:github.com deep-research-agent",
            "judge_site_operator",
        ),
        (
            "Compare the weather in Tokyo during Spring, Summer, Autumn, and Winter.",
            "judge_tokyo_weather",
        ),
        (
            "filetype:pdf annual report 2023 tesla",
            "judge_filetype_pdf",
        ),
        (
            "Compare Solid State Batteries and Lithium-Ion Batteries, focusing on energy density and safety. Be thorough.",
            "judge_batteries_rich",
        ),
        (
            "Detailed biological analysis of unicorns living on Mars surface in 2025.",
            "judge_sparse_failure",
        ),
    ],
)
async def test_searcher_run_is_judged_end_to_end(run_searcher, judge_llm, goal: str, trace_name: str):
    print("\n" + "=" * 120)
    print(f"Judged integration case: {trace_name}")
    print(f"Goal: {goal}")
    print("=" * 120 + "\n")

    state, events, _result, trace_path = await run_searcher(
        user_msg=goal,
        trace_name=trace_name,
    )

    evidence_summary = state.research_turn.evidence.get_summary()

    tool_events = []
    for ev in events:
        if ev.type == "ToolCall":
            tool_events.append(
                {
                    "type": "ToolCall",
                    "tool_name": ev.tool_name,
                    "tool_kwargs": ev.tool_kwargs,
                }
            )
        elif ev.type == "ToolCallResult":
            out = ev.tool_output
            out_str = str(out)
            if len(out_str) > 1500:
                out_str = out_str[:1500] + "...<truncated>"
            tool_events.append(
                {
                    "type": "ToolCallResult",
                    "tool_name": ev.tool_name,
                    "tool_output": out_str,
                }
            )

    trace_json = json.dumps(tool_events, indent=2, default=str)

    prompt = PromptTemplate(template=JUDGE_PROMPT)
    verdict = await judge_llm.astructured_predict(
        SearcherJudgeVerdict,
        prompt=prompt,
        goal=goal,
        trace_json=trace_json,
        evidence_summary=evidence_summary,
    )

    print("\nJudge verdict:")
    print(json.dumps(verdict.model_dump(), indent=2, default=str))
    print(f"\nTrace saved: {trace_path}")

    payload = {
        "goal": goal,
        "verdict": verdict.model_dump(),
        "trace_path": str(trace_path),
    }
    assert verdict.stopped_ok, json.dumps(payload, indent=2)
    assert verdict.decomposition_ok, json.dumps(payload, indent=2)
    assert verdict.search_and_read_ok, json.dumps(payload, indent=2)
    assert verdict.passed, json.dumps(payload, indent=2)
