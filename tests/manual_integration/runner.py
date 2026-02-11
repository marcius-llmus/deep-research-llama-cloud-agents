import asyncio
import difflib
import json
from typing import Any

from workflows import Context

from deep_research.services.models import ParsedDocumentAsset
from deep_research.workflows.research.state_keys import ReportStateKey, ReportStatus, StateNamespace
from deep_research.workflows.research.writer.agent import workflow as writer_agent


def _redact_tool_kwargs(tool_kwargs: Any) -> Any:
    if not isinstance(tool_kwargs, dict):
        return tool_kwargs
    redacted = tool_kwargs.copy()
    if "diff" in redacted:
        diff = redacted["diff"]
        size = len(diff) if isinstance(diff, str) else 0
        redacted["diff"] = f"<redacted patch {size} chars>"
    return redacted


def _format_event(ev: Any) -> str | None:
    name = type(ev).__name__

    if name == "ToolCall":
        kwargs = _redact_tool_kwargs(ev.tool_kwargs)
        return f"ToolCall(name={ev.tool_name}, id={ev.tool_id}, kwargs={kwargs})"

    if name == "ToolCallResult":
        return f"ToolCallResult(name={ev.tool_name}, id={ev.tool_id}, output={ev.tool_output})"

    return None


def _format_unified_diff(*, before: str, after: str, fromfile: str = "before", tofile: str = "after") -> str:
    diff_lines = difflib.unified_diff(
        (before or "").splitlines(True),
        (after or "").splitlines(True),
        fromfile=fromfile,
        tofile=tofile,
    )
    return "".join(diff_lines).strip()


async def _ensure_writer_state(ctx: Context) -> None:
    async with ctx.store.edit_state() as state:
        if StateNamespace.REPORT not in state:
            state[StateNamespace.REPORT] = {
                ReportStateKey.PATH: "artifacts/report.md",
                ReportStateKey.CONTENT: "",
                ReportStateKey.STATUS: ReportStatus.RUNNING,
            }


def _build_fake_research_notes(topic: str) -> str:
    assets = [
        ParsedDocumentAsset(
            id="synthetic_image_1",
            type="image",
            url="https://example.com/assets/diagram.png",
            description=f"High-level architecture diagram for {topic}",
            is_selected=True,
        )
    ]

    sources = [
        {
            "url": "https://example.com/overview",
            "title": f"Overview: {topic}",
            "metadata": {"source": "synthetic", "topic": topic},
            "content": (
                f"This is synthetic evidence about {topic}.\n\n"
                "Key points:\n"
                "- Provide a clear definition and scope boundaries.\n"
                "- Identify key components and how they interact.\n"
                "- Note typical risks and mitigations.\n"
            ),
            "assets": assets,
        },
        {
            "url": "https://example.com/data",
            "title": f"Data points: {topic}",
            "metadata": {"source": "synthetic", "topic": topic, "year": 2025},
            "content": (
                "Synthetic metrics (illustrative only):\n"
                "- Adoption: 35% -> 52% over 24 months in a sample cohort.\n"
                "- Cost impact: -18% median operational cost after standardization.\n"
                "- Quality: +12% improvement on a proxy KPI (reduced error rates).\n"
            ),
            "assets": [],
        },
        {
            "url": "https://example.com/implementation",
            "title": f"Implementation notes: {topic}",
            "metadata": {"source": "synthetic", "topic": topic},
            "content": (
                "Implementation guidance:\n"
                "1. Start with a minimal viable structure and iterate.\n"
                "2. Define ownership, review cadence, and acceptance criteria.\n"
                "3. Automate validation/CI checks where possible.\n\n"
                "Common failure modes:\n"
                "- Over-scoping initially.\n"
                "- Missing feedback loops with users/stakeholders.\n"
            ),
            "assets": [],
        },
    ]

    sections: list[str] = []
    for src in sources:
        header = f"### Source: {src['title']} ({src['url']})"

        meta_section = ""
        if src["metadata"]:
            meta_lines = ["**Metadata:**"]
            for k, v in src["metadata"].items():
                meta_lines.append(f"- {k}: {v}")
            meta_section = "\n".join(meta_lines)

        assets_section = ""
        if src["assets"]:
            assets_lines = ["**Relevant Assets:**"]
            for asset in src["assets"]:
                desc = asset.description or "Asset"
                if asset.type == "image":
                    assets_lines.append(f"![{desc}]({asset.url})")
                else:
                    assets_lines.append(f"- [{asset.type}] {desc} ({asset.url})")
            assets_section = "\n".join(assets_lines)

        parts = [header]
        if meta_section:
            parts.append(meta_section)
        if assets_section:
            parts.append(assets_section)
        parts.append(src["content"])

        sections.append("\n\n".join(parts))

    return "\n\n---\n\n".join(sections)


def _build_writer_user_msg(*, instruction: str, research_notes: str, review_feedback: str | None) -> str:
    user_msg = "Update the report based on the following research notes and instructions.\n\n"
    if review_feedback:
        user_msg += f"Review Feedback:\n<feedback>{review_feedback}</feedback>\n\n"
    user_msg += f"Research Notes:\n<research_notes>{research_notes}</research_notes>\n\n"
    user_msg += f"Instruction: {instruction}"
    return user_msg


def _print_report_snapshot(state: dict) -> None:
    report = state.get(StateNamespace.REPORT, {})
    content = report.get(ReportStateKey.CONTENT, "")

    print("\n--- Report snapshot ---")
    print(f"chars: {len(content or '')}")
    print(f"status: {report.get(ReportStateKey.STATUS)}")


async def main() -> None:
    ctx = Context(writer_agent)
    await _ensure_writer_state(ctx)

    topic = "Deep research report generation"
    research_notes = _build_fake_research_notes(topic)
    review_feedback: str | None = None

    print(
        "Writer agent iterative runner\n\n"
        "Commands:\n"
        "  /topic <text>      - set topic and reseed synthetic evidence\n"
        "  /feedback <text>   - set review feedback (included in prompt)\n"
        "  /state             - print current report size\n"
        "  /state_json        - dump full ctx state as JSON\n"
        "  /report            - print current report markdown\n"
        "  /reset             - clear report content\n"
        "  /exit              - quit\n"
    )

    while True:
        user_msg = input("Instruction: ").strip()
        if not user_msg:
            continue

        if user_msg in {"/exit", "/quit"}:
            break

        if user_msg.startswith("/topic "):
            topic = user_msg[len("/topic ") :].strip() or topic
            research_notes = _build_fake_research_notes(topic)
            print(f"Reseeded synthetic evidence for topic={topic!r}.")
            continue

        if user_msg.startswith("/feedback "):
            review_feedback = user_msg[len("/feedback ") :].strip() or None
            print("Updated review feedback.")
            continue

        if user_msg == "/state":
            state = await ctx.store.get_state()
            _print_report_snapshot(state)
            continue

        if user_msg == "/state_json":
            state = await ctx.store.get_state()
            print(json.dumps(state, indent=2, default=str))
            continue

        if user_msg == "/report":
            state = await ctx.store.get_state()
            content = state.get(StateNamespace.REPORT, {}).get(ReportStateKey.CONTENT, "")
            print("\n--- Current report ---\n")
            print(content)
            continue

        if user_msg == "/reset":
            async with ctx.store.edit_state() as state:
                state[StateNamespace.REPORT][ReportStateKey.CONTENT] = ""
                state[StateNamespace.REPORT][ReportStateKey.STATUS] = ReportStatus.RUNNING
            print("Reset report state.")
            continue

        await _ensure_writer_state(ctx)

        state_before = await ctx.store.get_state()
        content_before = state_before.get(StateNamespace.REPORT, {}).get(ReportStateKey.CONTENT, "")

        print("\nWriterAgent running...")
        prompt = _build_writer_user_msg(
            instruction=user_msg,
            research_notes=research_notes,
            review_feedback=review_feedback,
        )
        handler = writer_agent.run(user_msg=prompt, ctx=ctx)

        async for ev in handler.stream_events():
            formatted = _format_event(ev)
            if formatted:
                print(f"Event: {formatted}")

        result = await handler
        print("\nWriterAgent response:\n")
        print(str(result.response))

        state = await ctx.store.get_state()
        content = state.get(StateNamespace.REPORT, {}).get(ReportStateKey.CONTENT, "")

        diff_text = _format_unified_diff(
            before=content_before,
            after=content,
            fromfile="artifacts/report.md (before)",
            tofile="artifacts/report.md (after)",
        )
        if diff_text:
            print("\n--- Report changes (unified diff) ---\n")
            print(diff_text)
        else:
            print("\n--- Report changes ---\n")
            print("(no changes)")


if __name__ == "__main__":
    asyncio.run(main())
