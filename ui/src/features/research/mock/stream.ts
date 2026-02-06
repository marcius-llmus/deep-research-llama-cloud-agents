import type {
  FunctionAgentEvent,
  ToolCallData,
  ToolCallResultData,
  AgentInputData,
  AgentStreamData,
  StopEventData,
} from "@/features/research/events";
import type { ResearchSession } from "@/features/research/types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function ts() {
  return new Date().toISOString();
}

function toolCallId() {
  return `call_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Mock stream that mirrors the real handler event stream contract:
 * AgentStream, ToolCall, ToolCallResult, AgentInput, AgentOutput, StopEvent, WorkflowCancelledEvent.
 */
export async function* streamMockResearchRun(
  session: ResearchSession,
): AsyncGenerator<FunctionAgentEvent> {
  const searchToolId = toolCallId();
  const updateToolId1 = toolCallId();
  const updateToolId2 = toolCallId();

  // Agent Input
  yield {
    ts: ts(),
    type: "AgentInput",
    data: {
      input: [{ role: "user", content: session.initial_query }],
      current_agent_name: "ResearchAgent",
    } satisfies AgentInputData,
  } satisfies FunctionAgentEvent;
  await sleep(500);

  // Agent streaming response
  yield {
    ts: ts(),
    type: "AgentStream",
    data: {
      delta: "Starting web research and synthesizing findings...",
      response: "Starting web research and synthesizing findings...",
      current_agent_name: "ResearchAgent",
    } satisfies AgentStreamData,
  } satisfies FunctionAgentEvent;
  await sleep(650);

  // Web search tool call
  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "web_search",
      tool_id: searchToolId,
      tool_kwargs: {
        query: session.plan.expanded_queries[0] ?? session.initial_query,
        max_results: 5,
      },
    } satisfies ToolCallData,
  } satisfies FunctionAgentEvent;
  await sleep(800);

  // Web search result
  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "web_search",
      tool_id: searchToolId,
      tool_kwargs: { query: session.plan.expanded_queries[0] ?? session.initial_query, max_results: 5 },
      tool_output: {
        content: "Found 2 results:\n1. Source 1 - https://example.com/source-1\n2. Source 2 - https://example.com/source-2",
        tool_name: "web_search",
        is_error: false,
      },
      return_direct: false,
    } satisfies ToolCallResultData,
  } satisfies FunctionAgentEvent;
  await sleep(650);

  // First update_report tool call
  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "update_report",
      tool_id: updateToolId1,
      tool_kwargs: { max_update_size: 800 },
    } satisfies ToolCallData,
  } satisfies FunctionAgentEvent;
  await sleep(700);

  // First update_report result (UI treats new_report_markdown as authoritative)
  const report1 =
    session.report_markdown +
    "\n\n## Landscape overview\n\n- Tooling typically spans tracing, evals, and feedback loops.\n- Strong choices integrate OpenTelemetry semantics and LLM-specific spans.";

  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "update_report",
      tool_id: updateToolId1,
      tool_kwargs: { max_update_size: 800 },
      tool_output: {
        content: "Report updated with Landscape overview section.",
        tool_name: "update_report",
        is_error: false,
      },
      return_direct: false,
      new_report_markdown: report1,
    } satisfies ToolCallResultData,
  } satisfies FunctionAgentEvent;
  await sleep(650);

  // Second update_report tool call
  yield {
    ts: ts(),
    type: "ToolCall",
    data: {
      tool_name: "update_report",
      tool_id: updateToolId2,
      tool_kwargs: { max_update_size: 800 },
    } satisfies ToolCallData,
  } satisfies FunctionAgentEvent;
  await sleep(700);

  // Second update_report result
  const report2 =
    report1 +
    "\n\n## Recommended architecture\n\n1. Capture traces + metrics with OpenTelemetry.\n2. Add LLM-specific eval harnesses for regression testing.\n3. Record prompts/responses with redaction and retention policies.";

  yield {
    ts: ts(),
    type: "ToolCallResult",
    data: {
      tool_name: "update_report",
      tool_id: updateToolId2,
      tool_kwargs: { max_update_size: 800 },
      tool_output: {
        content: "Report updated with Recommended architecture section.",
        tool_name: "update_report",
        is_error: false,
      },
      return_direct: false,
      new_report_markdown: report2,
    } satisfies ToolCallResultData,
  } satisfies FunctionAgentEvent;
  await sleep(650);

  // Stop event
  yield {
    ts: ts(),
    type: "StopEvent",
    data: {
      result: { status: "completed", research_id: session.research_id },
    } satisfies StopEventData,
  } satisfies FunctionAgentEvent;
}
