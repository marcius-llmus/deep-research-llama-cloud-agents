// Event type discriminator
export type AgentEventType =
  | "AgentStream"
  | "ToolCall"
  | "ToolCallResult"
  | "AgentInput"
  | "AgentOutput"
  | "StopEvent"
  | "WorkflowCancelledEvent";

// Typed event data payloads (matching the Python event classes)
export type AgentStreamData = {
  delta: string;
  response: string;
  current_agent_name: string;
  tool_calls?: Array<{ tool_id: string; tool_name: string }>;
  thinking_delta?: string;
};

export type ToolCallData = {
  tool_name: string;
  tool_kwargs: Record<string, unknown>;
  tool_id: string;
};

export type ToolCallResultData = {
  tool_name: string;
  tool_kwargs: Record<string, unknown>;
  tool_id: string;
  tool_output: {
    content: string;
    tool_name: string;
    raw_input?: Record<string, unknown>;
    raw_output?: unknown;
    is_error?: boolean;
  };
  return_direct: boolean;
  // For update_report tool, we include the new report
  new_report_markdown?: string;
};

export type AgentInputData = {
  input: Array<{ role: string; content: string }>;
  current_agent_name: string;
};

export type AgentOutputData = {
  response: { role: string; content: string };
  current_agent_name: string;
  tool_calls?: Array<{ tool_id: string; tool_name: string }>;
};

export type StopEventData = {
  result?: unknown;
};

export type WorkflowCancelledData = {
  reason?: string;
};

// Union of all event data types
export type AgentEventData =
  | AgentStreamData
  | ToolCallData
  | ToolCallResultData
  | AgentInputData
  | AgentOutputData
  | StopEventData
  | WorkflowCancelledData;

// The main event type used throughout the UI
export type FunctionAgentEvent = {
  ts: string;
  type: AgentEventType;
  data: Record<string, unknown>;
};

// Type guards for event data
export function isToolCall(event: FunctionAgentEvent): event is FunctionAgentEvent & { data: ToolCallData } {
  return event.type === "ToolCall";
}

export function isToolCallResult(event: FunctionAgentEvent): event is FunctionAgentEvent & { data: ToolCallResultData } {
  return event.type === "ToolCallResult";
}

export function isAgentStream(event: FunctionAgentEvent): event is FunctionAgentEvent & { data: AgentStreamData } {
  return event.type === "AgentStream";
}
