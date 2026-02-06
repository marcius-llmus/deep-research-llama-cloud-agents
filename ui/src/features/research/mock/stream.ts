import type { FunctionAgentEvent } from "@/features/research/events";
import type { ResearchSession } from "@/features/research/types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function ts() {
  return new Date().toISOString();
}

/**
 * Mock stream that mirrors the real handler event stream contract:
 * AgentStream, ToolCall, ToolCallResult, AgentInput, AgentOutput, StopEvent, WorkflowCancelledEvent.
 */
export async function* streamMockResearchRun(
  session: ResearchSession,
): AsyncGenerator<FunctionAgentEvent> {
  yield {
    ts: ts(),
    type: "AgentInput",
    data: { message: session.initial_query },
  };
  await sleep(500);

  yield {
    ts: ts(),
    type: "AgentStream",
    data: { delta: "Starting web research and synthesizing findings..." },
  };
  await sleep(650);

  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "web_search",
      tool_kwargs: {
        query: session.plan.expanded_queries[0] ?? session.initial_query,
        max_results: 5,
      },
    },
  };
  await sleep(800);

  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "web_search",
      tool_output: [
        {
          url: "https://example.com/source-1",
          title: "Source 1",
          snippet: "A relevant source about the topic.",
        },
        {
          url: "https://example.com/source-2",
          title: "Source 2",
          snippet: "Another relevant source about the topic.",
        },
      ],
    },
  };
  await sleep(650);

  // The UI treats ToolCallResult(update_report).new_report_markdown as the authoritative report update.
  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "update_report",
      tool_kwargs: { max_update_size: 800 },
    },
  };
  await sleep(700);

  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "update_report",
      new_report_markdown:
        session.report_markdown +
        "\n## Landscape overview\n\n- Tooling typically spans tracing, evals, and feedback loops.\n- Strong choices integrate OpenTelemetry semantics and LLM-specific spans.\n",
    },
  };
  await sleep(650);

  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "update_report",
      tool_kwargs: { max_update_size: 800 },
    },
  };
  await sleep(700);

  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "update_report",
      new_report_markdown:
        session.report_markdown +
        "\n## Landscape overview\n\n- Tooling typically spans tracing, evals, and feedback loops.\n- Strong choices integrate OpenTelemetry semantics and LLM-specific spans.\n\n" +
        "## Recommended architecture\n\n1. Capture traces + metrics with OpenTelemetry.\n2. Add LLM-specific eval harnesses for regression testing.\n3. Record prompts/responses with redaction and retention policies.\n",
    },
  };
  await sleep(650);

  yield {
    ts: ts(),
    type: "StopEvent",
    data: { result: { status: "completed" } },
  };
}

