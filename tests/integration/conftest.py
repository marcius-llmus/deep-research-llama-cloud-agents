import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

import pytest
from workflows import Context

from llama_index.llms.google_genai import GoogleGenAI

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
        # --- BATTERIES (Solid State vs Li-ion) ---
        # High Relevance
        {
            "title": "Solid-State Batteries: The Future of Energy Storage?",
            "url": "https://tech-example.com/solid-state",
            "desc": "Solid-state batteries promise higher energy density (500 Wh/kg) compared to traditional lithium-ion cells.",
        },
        {
            "title": "Lithium-Ion Batteries Explained",
            "url": "https://energy-example.com/li-ion",
            "desc": "Lithium-ion batteries are the standard. Energy density tops out around 250-300 Wh/kg. Thermal runaway is a risk.",
        },
        {
            "title": "Battery Safety: Solid State vs Liquid Electrolyte",
            "url": "https://safety-example.org/battery-safety",
            "desc": "Liquid electrolytes in Li-ion are flammable. Solid electrolytes are non-flammable, reducing thermal runaway risk significantly.",
        },
        {
            "title": "Thermal Runaway in EV Batteries",
            "url": "https://ev-safety.com/thermal-runaway",
            "desc": "Analysis of fire risks in modern EVs. Comparison of BMS systems and cell chemistry safety profiles.",
        },
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
        # Medium Relevance / Niche
        {
            "title": "Toyota's Solid State Roadmap",
            "url": "https://auto-news.com/toyota-battery",
            "desc": "Toyota plans to launch solid-state EVs by 2027. Focus on charging speed (10 mins) and range (1200km).",
        },
        {
            "title": "Recycling Lithium-Ion Batteries",
            "url": "https://green-tech.org/recycling",
            "desc": "New methods for recovering cobalt and lithium from spent EV packs. Circular economy impact.",
        },
        {
            "title": "Sodium-Ion: The Cheaper Alternative?",
            "url": "https://chem-daily.com/sodium-ion",
            "desc": "Sodium-ion batteries are cheaper than Li-ion but have lower energy density. Good for grid storage.",
        },
        
        # --- AI MODELS (LLMs, Diffusion) ---
        {
            "title": "GPT-4 Architecture Leaks and Speculation",
            "url": "https://ai-insider.com/gpt4-arch",
            "desc": "Rumors of Mixture of Experts (MoE) architecture. 1.8 trillion parameters total.",
        },
        {
            "title": "Training Costs of Large Language Models",
            "url": "https://compute-daily.com/training-costs",
            "desc": "Training a frontier model now costs over $100M in compute. H100 GPU shortages continue.",
        },
        {
            "title": "Stable Diffusion vs Midjourney",
            "url": "https://art-tech.net/sd-vs-mj",
            "desc": "Comparison of open-source vs closed-source image generation models. ControlNet usage.",
        },
        {
            "title": "The Ethics of AI Alignment",
            "url": "https://philosophy-ai.org/alignment",
            "desc": "RLHF and Constitutional AI. How to prevent models from generating harmful content.",
        },

        # --- CLIMATE CHANGE ---
        {
            "title": "IPCC Report 2024 Summary",
            "url": "https://climate-watch.org/ipcc-2024",
            "desc": "Global temperatures have risen 1.2C. Urgent action needed to stay below 1.5C.",
        },
        {
            "title": "Carbon Capture Technologies",
            "url": "https://engineering-green.com/ccs",
            "desc": "Direct Air Capture (DAC) vs Point Source Capture. Costs are still prohibitive ($600/ton).",
        },
        {
            "title": "Renewable Energy Growth in Asia",
            "url": "https://energy-stats.com/asia-renewables",
            "desc": "Solar and wind adoption in China and India is outpacing expectations.",
        },

        # --- DISTRACTORS / IRRELEVANT ---
        {
            "title": "Best Solid State Drives (SSD) for Gaming 2024",
            "url": "https://pc-gamer.com/best-ssd",
            "desc": "Top NVMe drives from Samsung and WD. Load times comparison.",
        },
        {
            "title": "Lithium Mining Stocks to Watch",
            "url": "https://finance-daily.com/lithium-stocks",
            "desc": "Investment advice for the EV boom. Albemarle and SQM analysis.",
        },
        {
            "title": "How to Bake a Solid Cake",
            "url": "https://cooking-blog.com/solid-cake",
            "desc": "Recipes for dense, moist cakes. Tips for baking at high altitude.",
        },

        # --- DOJ / NEWS ---
        {
            "title": "DOJ Press Release: Example Enforcement Action",
            "url": "https://justice-example.gov/press/doj-enforcement",
            "desc": "Department of Justice announces an enforcement action. Official press release.",
        },
        {
            "title": "DOJ Newsroom Updates",
            "url": "https://justice-example.gov/news",
            "desc": "Latest DOJ newsroom updates and announcements.",
        },

        # --- WEATHER (Tokyo seasons) ---
        {
            "title": "Tokyo Weather in Spring (March-May)",
            "url": "https://weather-example.com/tokyo-spring",
            "desc": "Typical temperatures, rainfall, and conditions in Tokyo during spring.",
        },
        {
            "title": "Tokyo Weather in Summer (June-August)",
            "url": "https://weather-example.com/tokyo-summer",
            "desc": "Hot and humid season, rainy period, and typical temperature ranges.",
        },
        {
            "title": "Tokyo Weather in Autumn (September-November)",
            "url": "https://weather-example.com/tokyo-autumn",
            "desc": "Comfortable temperatures and precipitation patterns for Tokyo in autumn.",
        },
        {
            "title": "Tokyo Weather in Winter (December-February)",
            "url": "https://weather-example.com/tokyo-winter",
            "desc": "Cool and dry season details including average lows and highs.",
        },

        # --- GITHUB / SITE OPERATOR ---
        {
            "title": "deep-research-agent repository",
            "url": "https://github.com/example/deep-research-agent",
            "desc": "Repository containing a deep research agent example.",
        },

        # --- FILETYPE:PDF / TESLA REPORT ---
        {
            "title": "Tesla Annual Report 2023 (PDF)",
            "url": "https://reports-example.com/tesla-annual-report-2023.pdf",
            "desc": "Annual report for Tesla (2023). PDF document.",
        },
    ]


@pytest.fixture
def canned_pages() -> dict[str, bytes]:
    items: list[tuple[str, bytes]] = [
        # --- BATTERIES ---
        (
            "https://tech-example.com/solid-state",
            b"<html><head><title>Solid-State Batteries</title></head>"
            b"<body><h1>Solid-State Batteries: The Future?</h1>"
            b"<p>Solid-state batteries use a solid electrolyte instead of a liquid one. "
            b"This allows for higher energy density (up to 500 Wh/kg) and improved safety as they are less flammable.</p>"
            b"<h2>Why they matter</h2>"
            b"<p>They could revolutionize EVs by extending range to 800+ miles and reducing charging time to 10 minutes.</p>"
            b"<h2>Challenges</h2>"
            b"<p>Manufacturing costs are currently high, and dendrite formation remains a technical hurdle.</p>"
            b"<h2>Types of Solid Electrolytes</h2>"
            b"<ul><li>Oxides: Stable but brittle.</li><li>Sulfides: High conductivity but sensitive to moisture.</li><li>Polymers: Easy to process but lower conductivity.</li></ul>"
            b"</body></html>"
        ),
        (
            "https://energy-example.com/li-ion",
            b"<html><head><title>Lithium-Ion Batteries</title></head>"
            b"<body><h1>Lithium-Ion Batteries Explained</h1>"
            b"<p>Li-ion batteries use liquid electrolytes to move ions between cathode and anode. "
            b"They are mature, cheap to manufacture ($130/kWh), and reliable.</p>"
            b"<h2>Importance</h2>"
            b"<p>They power everything from phones to Teslas. The supply chain is established.</p>"
            b"<h2>Downsides</h2>"
            b"<p>Thermal runaway risks and lower theoretical energy density limits (approx 250 Wh/kg) compared to solid-state.</p>"
            b"<h2>Chemistry Types</h2>"
            b"<p>NMC (Nickel Manganese Cobalt) offers high density. LFP (Lithium Iron Phosphate) is cheaper and safer but less dense.</p>"
            b"</body></html>"
        ),
        (
            "https://safety-example.org/battery-safety",
            b"<html><body><h1>Safety Comparison</h1>"
            b"<p>Solid state batteries are safer because they do not use flammable liquid electrolytes.</p>"
            b"<h2>Thermal Runaway</h2>"
            b"<p>Liquid electrolytes can catch fire at 60C. Solid electrolytes are stable up to 200C+.</p>"
            b"</body></html>"
        ),
        (
            "https://ev-safety.com/thermal-runaway",
            b"<html><body><h1>Thermal Runaway</h1>"
            b"<p>Thermal runaway is a major risk in Li-ion batteries.</p>"
            b"<p>It occurs when a cell short-circuits and generates heat faster than it can dissipate.</p>"
            b"<h2>Prevention</h2>"
            b"<p>BMS (Battery Management Systems) monitor temp. Liquid cooling helps.</p>"
            b"</body></html>"
        ),
        (
            "https://market-example.net/battery-cost",
            b"<html><body><h1>Battery Costs</h1>"
            b"<p>Li-ion is cheap ($130/kWh). Solid state is expensive ($800/kWh estimated).</p>"
            b"<p>Price parity is expected by 2030 if manufacturing scales.</p>"
            b"</body></html>"
        ),
        (
            "https://tech-news.com/quantumscape",
            b"<html><body><h1>QuantumScape News</h1>"
            b"<p>Working on solving dendrite issues using a ceramic separator.</p>"
            b"<p>Stock is volatile. Partners with VW.</p>"
            b"</body></html>"
        ),
        (
            "https://auto-news.com/toyota-battery",
            b"<html><body><h1>Toyota's Roadmap</h1><p>Toyota aims for 2027 launch. 1200km range target.</p></body></html>"
        ),
        (
            "https://green-tech.org/recycling",
            b"<html><body><h1>Battery Recycling</h1><p>Hydrometallurgy vs Pyrometallurgy. 95% recovery rates possible.</p></body></html>"
        ),
        (
            "https://chem-daily.com/sodium-ion",
            b"<html><body><h1>Sodium Ion</h1><p>No lithium needed. Good for stationary storage. Lower density (160 Wh/kg).</p></body></html>"
        ),

        # --- AI MODELS ---
        (
            "https://ai-insider.com/gpt4-arch",
            b"<html><body><h1>GPT-4 Architecture</h1><p>Likely MoE with 8 experts. 1.8T params.</p></body></html>"
        ),
        (
            "https://compute-daily.com/training-costs",
            b"<html><body><h1>Training Costs</h1><p>H100 clusters are expensive. GPT-4 cost >$60M to train.</p></body></html>"
        ),
        (
            "https://art-tech.net/sd-vs-mj",
            b"<html><body><h1>SD vs Midjourney</h1><p>SDXL is open weights. MJ v6 has better aesthetics.</p></body></html>"
        ),
        (
            "https://philosophy-ai.org/alignment",
            b"<html><body><h1>AI Alignment</h1><p>RLHF is the standard. Constitutional AI uses AI to critique AI.</p></body></html>"
        ),

        # --- CLIMATE ---
        (
            "https://climate-watch.org/ipcc-2024",
            b"<html><body><h1>IPCC 2024</h1><p>1.5C target is slipping. Methane reduction is critical.</p></body></html>"
        ),
        (
            "https://engineering-green.com/ccs",
            b"<html><body><h1>Carbon Capture</h1><p>DAC is energy intensive. Point source is cheaper.</p></body></html>"
        ),
        (
            "https://energy-stats.com/asia-renewables",
            b"<html><body><h1>Asia Renewables</h1><p>China installed 200GW of solar in 2023.</p></body></html>"
        ),

        # --- DISTRACTORS ---
        (
            "https://pc-gamer.com/best-ssd",
            b"<html><body><h1>Best SSDs</h1><p>Samsung 990 Pro is top tier. Gen5 drives are hot.</p></body></html>"
        ),
        (
            "https://finance-daily.com/lithium-stocks",
            b"<html><body><h1>Lithium Stocks</h1><p>Buy low, sell high. Volatile market.</p></body></html>"
        ),
        (
            "https://cooking-blog.com/solid-cake",
            b"<html><body><h1>Solid Cake Recipe</h1><p>Use more flour. Bake at 350F.</p></body></html>"
        ),

        # --- DOJ / NEWS ---
        (
            "https://justice-example.gov/press/doj-enforcement",
            b"<html><body><h1>DOJ Enforcement Action</h1><p>DOJ announced an enforcement action. This is an official press release.</p></body></html>",
        ),
        (
            "https://justice-example.gov/news",
            b"<html><body><h1>DOJ Newsroom</h1><p>Latest DOJ newsroom updates and announcements.</p></body></html>",
        ),

        # --- WEATHER (Tokyo seasons) ---
        (
            "https://weather-example.com/tokyo-spring",
            b"<html><body><h1>Tokyo Spring Weather</h1><p>Spring is mild. Average highs 15-22C, with moderate rainfall.</p></body></html>",
        ),
        (
            "https://weather-example.com/tokyo-summer",
            b"<html><body><h1>Tokyo Summer Weather</h1><p>Summer is hot and humid. Average highs 28-33C. Rainy season occurs in early summer.</p></body></html>",
        ),
        (
            "https://weather-example.com/tokyo-autumn",
            b"<html><body><h1>Tokyo Autumn Weather</h1><p>Autumn is cooler and comfortable. Average highs 18-26C. Rainfall decreases compared to summer.</p></body></html>",
        ),
        (
            "https://weather-example.com/tokyo-winter",
            b"<html><body><h1>Tokyo Winter Weather</h1><p>Winter is cool and relatively dry. Average highs 8-12C, lows 1-5C.</p></body></html>",
        ),

        # --- GITHUB ---
        (
            "https://github.com/example/deep-research-agent",
            b"<html><body><h1>deep-research-agent</h1><p>Example repository for a deep research agent.</p></body></html>",
        ),

        # --- PDF ---
        (
            "https://reports-example.com/tesla-annual-report-2023.pdf",
            b"<html><body><h1>Tesla Annual Report 2023</h1><p>PDF content placeholder: annual report highlights.</p></body></html>",
        ),
    ]

    pages: dict[str, bytes] = {}
    duplicates: list[str] = []
    for url, content in items:
        if url in pages:
            duplicates.append(url)
            continue
        pages[url] = content

    if duplicates:
        raise ValueError(f"Duplicate URLs detected in canned_pages fixture: {sorted(set(duplicates))}")

    return pages


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
def judge_llm() -> GoogleGenAI:
    model = os.getenv("JUDGE_MODEL", "gemini-2.5-flash-lite").strip() or "gemini-2.5-flash-lite"
    return GoogleGenAI(model=model, temperature=0)


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
            
            if "query" in tool_kwargs:
                print(f"   Query: {tool_kwargs['query']}", flush=True)
            elif "original_query" in tool_kwargs:
                print(f"   Query: {tool_kwargs['original_query']}", flush=True)
            elif "urls" in tool_kwargs:
                print(f"   URLs: {len(tool_kwargs['urls'])} items", flush=True)

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
        handler = searcher_agent.run(user_msg=user_msg, ctx=ctx, max_iterations=60)
        
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
