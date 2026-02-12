import pytest


@pytest.mark.asyncio
async def test_searcher_finishes_and_collects_evidence(run_searcher):
    state, events, result, trace_path = await run_searcher(
        user_msg="Compare Solid State Batteries and Lithium-Ion Batteries, focusing on energy density and safety. Be thorough.",
        trace_name="finishes_and_collects_evidence",
    )

    assert state.research_turn.evidence.items
    assert state.research_turn.seen_urls
    assert any(e.type == "ToolCall" for e in events)
    assert trace_path.exists()


@pytest.mark.asyncio
async def test_searcher_tool_order_contract(run_searcher):
    state, events, result, trace_path = await run_searcher(
        user_msg="Find high-quality sources about Solid-State Batteries and their manufacturing costs.",
        trace_name="tool_order_contract",
    )

    tool_calls = [e for e in events if e.type == "ToolCall"]
    tool_names = [e.tool_name for e in tool_calls]

    if tool_names:
        assert tool_names[0] == "decompose_query"

    if "verify_research_sufficiency" in tool_names:
        assert "generate_evidences" in tool_names
        assert tool_names.index("generate_evidences") < tool_names.index("verify_research_sufficiency")

    assert state.research_turn.evidence.items
