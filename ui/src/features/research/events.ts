export type FunctionAgentEventType =
  | "AgentStream"
  | "ToolCall"
  | "ToolCallResult"
  | "AgentInput"
  | "AgentOutput"
  | "StopEvent"
  | "WorkflowCancelledEvent";

export type FunctionAgentEvent = {
  ts: string;
  type: FunctionAgentEventType;
  data: Record<string, unknown>;
};

