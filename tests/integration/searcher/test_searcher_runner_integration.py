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
        assert tool_names[0] == "plan_search_queries"

    assert state.research_turn.evidence.items


@pytest.mark.asyncio
async def test_searcher_parallel_execution(run_searcher):
    """
    Verifies that the searcher agent executes multiple web_search calls for a complex query
    that requires comparing two distinct topics.
    """
    goal = "Compare Solid State Batteries and Lithium-Ion Batteries, focusing on energy density and safety. Be thorough."
    
    state, events, result, trace_path = await run_searcher(
        user_msg=goal,
        trace_name="parallel_execution_test",
    )

    web_search_calls = [
        ev for ev in events 
        if ev.type == "ToolCall" and ev.tool_name == "web_search"
    ]

    assert len(web_search_calls) >= 2, f"Expected at least 2 web_search calls, got {len(web_search_calls)}"

    queries = {ev.tool_kwargs.get("query") for ev in web_search_calls}
    assert len(queries) >= 2, f"Expected at least 2 unique queries, got {len(queries)}"
