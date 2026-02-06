import type { ResearchSession } from "@/features/research/types";

const nowIso = () => new Date().toISOString();

// Keep mock sessions stable across navigations and page refreshes.
// (In the real app, sessions come from Agent Data.)
const MOCK_CREATED_AT = nowIso();
const MOCK_UPDATED_AT = MOCK_CREATED_AT;

const MOCK_SESSIONS: ResearchSession[] = [
  {
    research_id: "research_mock_001",
    created_at: MOCK_CREATED_AT,
    updated_at: MOCK_UPDATED_AT,
    status: "awaiting_approval",
    initial_query:
      "Assess the current state of open-source LLM observability tooling and recommend a stack for a 5-person team.",
    plan: {
      clarifying_questions: [
        "What is the primary environment (Kubernetes, serverless, on-prem)?",
        "Do you need PII redaction and audit logs?",
        "Which LLM providers/models are you using today?",
      ],
      expanded_queries: [
        "open source LLM observability tracing evals",
        "Langfuse vs OpenTelemetry LLM tracing",
        "prompt evaluation frameworks open source",
        "LLM security governance open source",
      ],
      outline: [
        "## Executive summary",
        "## Requirements",
        "## Landscape overview",
        "## Recommended architecture",
        "## Implementation plan",
        "## Risks and mitigations",
        "## References",
      ],
    },
    report_markdown:
      "# Deep Research Report\n\n## Executive summary\n\n(Report will update live once execution starts.)\n",
    sources: [
      {
        url: "https://example.com/llm-observability-overview",
        title: "LLM Observability Overview",
        snippet:
          "A survey of tracing, evaluation, and monitoring options for LLM apps.",
        retrieved_at: MOCK_CREATED_AT,
      },
    ],
    artifacts: [
      {
        file_id: "file_mock_001",
        name: "observability-landscape.pdf",
        kind: "pdf",
        created_at: MOCK_CREATED_AT,
        source_url: "https://example.com/observability-landscape.pdf",
      },
    ],
  },
  {
    research_id: "research_mock_002",
    created_at: MOCK_CREATED_AT,
    updated_at: MOCK_UPDATED_AT,
    status: "completed",
    initial_query:
      "Summarize the latest approaches for RAG evaluation and propose a lightweight evaluation protocol.",
    plan: {
      clarifying_questions: [
        "Do you evaluate in offline datasets, online A/B tests, or both?",
      ],
      expanded_queries: [
        "RAG evaluation metrics faithfulness answer relevancy",
        "LLM-as-judge reliability and calibration",
        "retrieval evaluation MRR nDCG RAG",
      ],
      outline: [
        "## Goal",
        "## Metrics and failure modes",
        "## Offline evaluation protocol",
        "## Online evaluation protocol",
        "## Suggested tooling",
        "## References",
      ],
    },
    report_markdown:
      "# Deep Research Report\n\n## Goal\n\nThis report summarizes current RAG evaluation practices...\n\n## References\n\n- ...\n",
    sources: [
      {
        url: "https://example.com/rag-evals",
        title: "RAG Evaluation Notes",
        snippet: "A practical overview of evaluation approaches.",
        retrieved_at: MOCK_CREATED_AT,
      },
    ],
    artifacts: [],
  },
];

export function listMockResearchSessions(): ResearchSession[] {
  // defensive copy
  return MOCK_SESSIONS.map((s) => ({
    ...s,
    plan: {
      ...s.plan,
      clarifying_questions: [...s.plan.clarifying_questions],
      expanded_queries: [...s.plan.expanded_queries],
      outline: [...s.plan.outline],
    },
    sources: s.sources.map((src) => ({ ...src })),
    artifacts: s.artifacts.map((a) => ({ ...a })),
  }));
}

export function getMockResearchSession(
  researchId: string,
): ResearchSession | undefined {
  return listMockResearchSessions().find((s) => s.research_id === researchId);
}

