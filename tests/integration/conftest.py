import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

import pytest
from workflows import Context

from deep_research.services.document_parser_service import DocumentParserService
from deep_research.services.file_service import FileService
from deep_research.services.models import ParsedDocument
from deep_research.services.web_search_service import WebSearchService
from deep_research.workflows.research.searcher.agent import workflow as searcher_agent
from deep_research.workflows.research.state import DeepResearchState, ResearchStateAccessor


@dataclass
class ToolEvent:
    type: str
    tool_name: str
    tool_id: str | None
    tool_kwargs: Any
    tool_output: Any


@pytest.fixture
def use_real_llm() -> bool:
    return os.getenv("USE_REAL_LLM", "0").strip() == "1"


@pytest.fixture
def canned_serp() -> list[dict[str, Any]]:
    return [
        # Energy Density
        {
            "title": "Solid-State Batteries: The Future of Energy Storage?",
            "url": "https://tech-example.com/solid-state",
            "desc": "Solid-state batteries promise higher energy density (500 Wh/kg) compared to traditional lithium-ion cells.",
        },
        {
            "title": "Lithium-Ion Batteries Explained",
            "url": "https://energy-example.com/li-ion",
            "desc": "Lithium-ion batteries are the standard. Energy density tops out around 250-300 Wh/kg.",
        },
        # Safety
        {
            "title": "Battery Safety: Solid State vs Liquid Electrolyte",
            "url": "https://safety-example.org/battery-safety",
            "desc": "Liquid electrolytes in Li-ion are flammable. Solid electrolytes are non-flammable, reducing thermal runaway risk.",
        },
        {
            "title": "Thermal Runaway in EV Batteries",
            "url": "https://ev-safety.com/thermal-runaway",
            "desc": "Analysis of fire risks in modern EVs. Comparison of BMS systems and cell chemistry safety profiles.",
        },
        # Cost / Market
        {
            "title": "The Cost of Battery Manufacturing 2025",
            "url": "https://market-example.net/battery-cost",
            "desc": "Li-ion costs have fallen to $130/kWh. Solid-state remains expensive to manufacture at scale.",
        },
        {
            "title": "QuantumScape and the Race for Solid State",
            "url": "https://tech-news.com/quantumscape",
            "desc": "Updates on solid-state commercialization. Challenges in dendrite formation and manufacturing throughput.",
        },
    ]


@pytest.fixture
def canned_pages() -> dict[str, bytes]:
    return {
        "https://tech-example.com/solid-state": (
            b"<html><head><title>Solid-State Batteries</title></head>"
            b"<body><h1>Solid-State Batteries: The Future?</h1>"
            b"<p>Solid-state batteries use a solid electrolyte instead of a liquid one. "
            b"This allows for higher energy density (up to 500 Wh/kg) and improved safety as they are less flammable.</p>"
            b"<h2>Why they matter</h2>"
            b"<p>They could revolutionize EVs by extending range to 800+ miles and reducing charging time to 10 minutes.</p>"
            b"<h2>Challenges</h2>"
            b"<p>Manufacturing costs are currently high, and dendrite formation remains a technical hurdle.</p></body></html>"
        ),
        "https://energy-example.com/li-ion": (
            b"<html><head><title>Lithium-Ion Batteries</title></head>"
            b"<body><h1>Lithium-Ion Batteries Explained</h1>"
            b"<p>Li-ion batteries use liquid electrolytes to move ions between cathode and anode. "
            b"They are mature, cheap to manufacture ($130/kWh), and reliable.</p>"
            b"<h2>Importance</h2>"
            b"<p>They power everything from phones to Teslas. The supply chain is established.</p>"
            b"<h2>Downsides</h2>"
            b"<p>Thermal runaway risks and lower theoretical energy density limits (approx 250 Wh/kg) compared to solid-state.</p></body></html>"
        ),
        "https://safety-example.org/battery-safety": (
            b"<html><body><h1>Safety Comparison</h1><p>Solid state batteries are safer because they do not use flammable liquid electrolytes.</p></body></html>"
        ),
        "https://ev-safety.com/thermal-runaway": (
            b"<html><body><h1>Thermal Runaway</h1><p>Thermal runaway is a major risk in Li-ion batteries.</p></body></html>"
        ),
        "https://market-example.net/battery-cost": (
            b"<html><body><h1>Battery Costs</h1><p>Li-ion is cheap ($130/kWh). Solid state is expensive.</p></body></html>"
        ),
        "https://tech-news.com/quantumscape": (
            b"<html><body><h1>QuantumScape News</h1><p>Working on solving dendrite issues.</p></body></html>"
        ),
    }


@pytest.fixture
def mock_external_calls(monkeypatch: pytest.MonkeyPatch, canned_serp: list[dict[str, Any]], canned_pages: dict[str, bytes]):
    async def _mock_search_google(self: WebSearchService, query: str, max_results: int = 10):
        # Simple keyword matching to simulate a real search engine
        query_terms = [t.lower() for t in query.split() if len(t) > 3]
        results = []
        
        # If no specific terms, return a mix
        if not query_terms:
            return canned_serp[:max_results], 1

        for item in canned_serp:
            text = (item["title"] + " " + item["desc"]).lower()
            if any(term in text for term in query_terms):
                results.append(item)
        
        # Fallback: if no matches found, return nothing (realistic) or generic (helpful)
        # Let's return generic if empty to avoid "no results" dead ends in simple tests,
        # but strictly speaking, a real engine might return nothing.
        if not results:
             # Return top 2 as fallback to keep agent moving
             results = canned_serp[:2]

        return results[:max_results], 1

    async def _mock_download_url_bytes(self: WebSearchService, url: str, use_render: bool = True, timeout: int = 10) -> bytes:
        return canned_pages.get(url, b"")

    async def _mock_upload_bytes(self: FileService, content: bytes, filename: str) -> str:
        return f"file_{abs(hash((filename, len(content))))}"

    async def _mock_parse_files(self: DocumentParserService, files: list[tuple[str, str]]):
        parsed: list[ParsedDocument] = []
        failed: list[str] = []
        for _file_id, url in files:
            raw = canned_pages.get(url)
            if not raw:
                failed.append(url)
                continue
            
            html = raw.decode("utf-8", errors="ignore")
            # Simple HTML to Markdown conversion for realism
            markdown = html
            markdown = re.sub(r'<h1>(.*?)</h1>', r'# \1\n', markdown, flags=re.IGNORECASE)
            markdown = re.sub(r'<h2>(.*?)</h2>', r'## \1\n', markdown, flags=re.IGNORECASE)
            markdown = re.sub(r'<h3>(.*?)</h3>', r'### \1\n', markdown, flags=re.IGNORECASE)
            markdown = re.sub(r'<p>(.*?)</p>', r'\1\n\n', markdown, flags=re.IGNORECASE)
            markdown = re.sub(r'<br\s*/?>', r'\n', markdown, flags=re.IGNORECASE)
            markdown = re.sub(r'<[^>]+>', '', markdown) # Remove remaining tags
            markdown = re.sub(r'\n\s+\n', '\n\n', markdown).strip()

            parsed.append(
                ParsedDocument(
                    source_url=url,
                    markdown=markdown,
                    assets=[],
                    metadata={"title": url.rsplit("/", 1)[-1].upper()},
                )
            )
        return parsed, failed

    monkeypatch.setattr(WebSearchService, "search_google", _mock_search_google)
    monkeypatch.setattr(WebSearchService, "download_url_bytes", _mock_download_url_bytes)
    monkeypatch.setattr(FileService, "upload_bytes", _mock_upload_bytes)
    monkeypatch.setattr(DocumentParserService, "parse_files", _mock_parse_files)


@pytest.fixture
def trace_dir(tmp_path: Path) -> Path:
    d = tmp_path / "traces"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _collect_tool_events(handler: Any) -> list[ToolEvent]:
    events: list[ToolEvent] = []
    is_streaming = False

    async for ev in handler.stream_events():
        name = type(ev).__name__

        # --- Real-time Output Logic ---

        if name == "AgentInput":
            if is_streaming:
                print()
                is_streaming = False
            
            # Extract user message
            input_obj = getattr(ev, "input", None)
            content = "Unknown Input"
            if isinstance(input_obj, list) and input_obj:  # List[ChatMessage]
                content = input_obj[-1].content
            elif hasattr(input_obj, "content"):
                content = input_obj.content
            elif isinstance(input_obj, str):
                content = input_obj
            
            print(f"\n👤 User: {content}", flush=True)
            continue

        if name == "AgentStream":
            delta = getattr(ev, "delta", "")
            if delta:
                print(delta, end="", flush=True)
                is_streaming = True
            continue

        if name == "ToolCall":
            if is_streaming:
                print()
                is_streaming = False
            
            tool_name = getattr(ev, "tool_name", "")
            tool_id = getattr(ev, "tool_id", "")
            tool_kwargs = getattr(ev, "tool_kwargs", {})
            
            # Pretty print tool call
            print(f"\n🔨 ToolCall: {tool_name}", flush=True)
            # print(f"   Kwargs: {json.dumps(tool_kwargs, default=str)}", flush=True)

            events.append(
                ToolEvent(
                    type="ToolCall",
                    tool_name=tool_name,
                    tool_id=str(tool_id) or None,
                    tool_kwargs=tool_kwargs,
                    tool_output=None,
                )
            )
            continue

        if name == "ToolCallResult":
            if is_streaming:
                print()
                is_streaming = False

            tool_name = getattr(ev, "tool_name", "")
            tool_id = getattr(ev, "tool_id", "")
            tool_output = getattr(ev, "tool_output", "")
            
            output_str = str(tool_output)
            preview = output_str[:200] + "..." if len(output_str) > 200 else output_str
            
            print(f"✅ ToolResult: {tool_name} -> {preview}", flush=True)

            events.append(
                ToolEvent(
                    type="ToolCallResult",
                    tool_name=tool_name,
                    tool_id=str(tool_id) or None,
                    tool_kwargs=None,
                    tool_output=tool_output,
                )
            )
            continue
        
        # Ignore AgentOutput (redundant with stream) and others for console noise
        # but you can log them if needed.

    if is_streaming:
        print()

    return events


@pytest.fixture
def run_searcher(
    mock_external_calls,
    trace_dir: Path,
) -> Callable[..., Coroutine[Any, Any, tuple[DeepResearchState, list[ToolEvent], Any, Path]]]:
    async def _run(*, user_msg: str, trace_name: str = "searcher"):
        ctx = Context(searcher_agent)
        handler = searcher_agent.run(user_msg=user_msg, ctx=ctx)
        
        # Collect events with real-time streaming
        events = await _collect_tool_events(handler)
        
        result = await handler
        state = await ResearchStateAccessor.get(ctx)
        trace_path = trace_dir / f"{trace_name}.json"
        
        payload = {
            "user_msg": user_msg,
            "result": str(getattr(result, "response", result)),
            "events": [asdict(e) for e in events],
            "state": state.model_dump(),
        }
        trace_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return state, events, result, trace_path

    return _run
