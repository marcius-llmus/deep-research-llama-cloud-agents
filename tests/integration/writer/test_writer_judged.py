import pytest
from pydantic import BaseModel, Field
from llama_index.core import PromptTemplate
from deep_research.workflows.research.state import DeepResearchState, ResearchArtifactState, ResearchTurnState
from deep_research.workflows.research.searcher.models import EvidenceBundle, EvidenceItem

class WriterJudgeVerdict(BaseModel):
    grounding_score: int = Field(..., ge=0, le=10)
    instruction_score: int = Field(..., ge=0, le=10)
    integrity_score: int = Field(..., ge=0, le=10)
    passed: bool
    reasoning: str

WRITER_JUDGE_PROMPT = """
You are a strict Editor-in-Chief auditing a technical writer's work.

**Input Context:**
1. <Original Report>: The markdown file before changes.
2. <Instruction>: The specific task given to the writer (e.g., "Add a section about X based on the notes").
3. <Research Notes>: The raw evidence/source material provided to the writer.
4. <Final Report>: The markdown file after the writer's changes.

**Your Task:**
Evaluate the <Final Report> based on the following criteria. You must output a JSON verdict.

**Evaluation Criteria:**
1. **Grounding (Critical):**
   - Did the writer ONLY use facts present in <Research Notes>?
   - Mark FAIL if the writer hallucinated information or brought in outside knowledge not in the notes.
   - Mark FAIL if the writer cited sources that do not exist in the notes.

2. **Instruction Adherence:**
   - Did the writer follow the <Instruction> exactly?
   - If asked to "add", did they add? If asked to "update", did they update?
   - Did they answer the specific question asked in the instruction?

3. **Content Integrity:**
   - Did the writer preserve the existing valid parts of <Original Report>?
   - Mark FAIL if they accidentally deleted unrelated sections (e.g., wiping out the Introduction while writing the Conclusion).

4. **Formatting:**
   - Is the result valid Markdown?
   - Are headers hierarchically consistent?

**Verdict Schema:**
{
  "grounding_score": (0-10),
  "instruction_score": (0-10),
  "integrity_score": (0-10),
  "passed": (boolean),
  "reasoning": "Short explanation of failures or success."
}

**Inputs:**

<Original Report>
{original_report}
</Original Report>

<Instruction>
{instruction}
</Instruction>

<Research Notes>
{research_notes}
</Research Notes>

<Final Report>
{final_report}
</Final Report>
"""

@pytest.mark.asyncio
async def test_writer_judged_add_section(run_writer, judge_llm):
    # Setup initial state
    original_report = "# My Report\n\n## Introduction\nThis is the intro."
    instruction = "Add a section about 'Cats' based on the notes."
    raw_research_notes = "Cats are small carnivorous mammals. They are the only domesticated species in the family Felidae."

    evidence = EvidenceBundle(
        items=[EvidenceItem(url="http://cats.com", content=raw_research_notes)]
    )
    research_notes = evidence.get_content_for_writing()

    writer_user_msg = f"Instruction: {instruction}"

    initial_state = DeepResearchState(
        research_artifact=ResearchArtifactState(content=original_report),
        research_turn=ResearchTurnState(
            evidence=evidence
        )
    ).model_dump()

    # Run writer
    state, events, result, trace_path = await run_writer(
        user_msg=writer_user_msg,
        initial_state=initial_state,
        trace_name="writer_add_section",
    )

    final_report = state.research_artifact.content

    # Judge
    prompt = PromptTemplate(template=WRITER_JUDGE_PROMPT)
    verdict = await judge_llm.astructured_predict(
        WriterJudgeVerdict,
        prompt=prompt,
        original_report=original_report,
        instruction=instruction,
        research_notes=research_notes,
        final_report=final_report,
    )

    print(f"\nJudge Verdict: {verdict.model_dump_json(indent=2)}")
    assert verdict.passed, f"Writer failed judge check: {verdict.reasoning}"
    assert verdict.grounding_score >= 8
    assert verdict.instruction_score >= 8
    assert verdict.integrity_score >= 8
    assert "Cats" in final_report
    assert "Introduction" in final_report # Integrity check
