from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.google_genai import GoogleGenAI

from deep_research.config import ResearchConfig
from deep_research.services.content_analysis_service import ContentAnalysisService
from deep_research.services.document_parser_service import DocumentParserService
from deep_research.services.evidence_service import EvidenceService
from deep_research.services.file_service import FileService
from deep_research.services.query_service import QueryService
from deep_research.services.web_search_service import WebSearchService
from deep_research.utils import load_config_from_json
from deep_research.workflows.research.searcher.prompts import build_research_system_prompt
from deep_research.workflows.research.searcher.tools import SearcherTools

cfg = load_config_from_json(
    model=ResearchConfig,
    config_file="configs/config.json",
    path_selector="research",
    label="Research Config",
    description="Deep research collection + settings",
)
searcher_cfg = cfg.searcher


def build_searcher_agent() -> FunctionAgent:
    llm = GoogleGenAI(
        model=searcher_cfg.main_llm.model,
        temperature=searcher_cfg.main_llm.temperature,
        reasoning={"thinking_level": "MEDIUM"},
    )

    web_search_service = WebSearchService()
    file_service = FileService()
    document_parser_service = DocumentParserService()

    query_service = QueryService(llm_config=searcher_cfg.main_llm)
    content_analysis_service = ContentAnalysisService(llm_config=searcher_cfg.weak_llm)

    evidence_service = EvidenceService(
        content_analysis_service=content_analysis_service,
        document_parser_service=document_parser_service,
        file_service=file_service,
        web_search_service=web_search_service,
    )

    tools_spec = SearcherTools(
        config=cfg,
        web_search_service=web_search_service,
        query_service=query_service,
        evidence_service=evidence_service,
    )
    tools = tools_spec.to_tool_list()

    finalize_tool = FunctionTool.from_defaults(
        fn=tools_spec.finalize_research,
        return_direct=True,
    )
    tools.append(finalize_tool)

    system_prompt = build_research_system_prompt()

    return FunctionAgent(
        name="SearcherAgent",
        description="An agent capable of performing deep research tasks with HITL support.",
        system_prompt=system_prompt,
        llm=llm,
        tools=tools,
        timeout=None,
    )
