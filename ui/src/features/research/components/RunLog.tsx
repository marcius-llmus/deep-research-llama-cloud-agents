import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Cpu,
  MessageSquare,
  Play,
  Square,
  Terminal,
  Wrench,
  XCircle,
} from "lucide-react";

import type {
  FunctionAgentEvent,
  ToolCallData,
  ToolCallResultData,
  AgentStreamData,
  AgentInputData,
  AgentOutputData,
} from "@/features/research/events";

type EventRowProps = {
  event: FunctionAgentEvent;
  defaultExpanded?: boolean;
};

function EventIcon({ type }: { type: FunctionAgentEvent["type"] }) {
  const iconClass = "h-4 w-4";
  switch (type) {
    case "AgentStream":
      return <MessageSquare className={`${iconClass} text-blue-500`} />;
    case "ToolCall":
      return <Wrench className={`${iconClass} text-amber-500`} />;
    case "ToolCallResult":
      return <Terminal className={`${iconClass} text-emerald-500`} />;
    case "AgentInput":
      return <Play className={`${iconClass} text-purple-500`} />;
    case "AgentOutput":
      return <Cpu className={`${iconClass} text-indigo-500`} />;
    case "StopEvent":
      return <Square className={`${iconClass} text-gray-500`} />;
    case "WorkflowCancelledEvent":
      return <XCircle className={`${iconClass} text-red-500`} />;
    default:
      return <Terminal className={iconClass} />;
  }
}

function formatEventTitle(event: FunctionAgentEvent): string {
  const { type, data } = event;
  switch (type) {
    case "AgentStream": {
      const d = data as AgentStreamData;
      const preview = d.delta?.slice(0, 60) || d.response?.slice(0, 60) || "";
      return preview ? `Stream: "${preview}${preview.length >= 60 ? "..." : ""}"` : "Agent streaming...";
    }
    case "ToolCall": {
      const d = data as ToolCallData;
      return `Tool call: ${d.tool_name}`;
    }
    case "ToolCallResult": {
      const d = data as ToolCallResultData;
      const status = d.tool_output?.is_error ? "failed" : "completed";
      return `Tool result: ${d.tool_name} (${status})`;
    }
    case "AgentInput": {
      const d = data as AgentInputData;
      return `Agent input → ${d.current_agent_name || "agent"}`;
    }
    case "AgentOutput": {
      const d = data as AgentOutputData;
      return `Agent output ← ${d.current_agent_name || "agent"}`;
    }
    case "StopEvent":
      return "Workflow completed";
    case "WorkflowCancelledEvent":
      return "Workflow cancelled";
    default:
      return type;
  }
}

function EventRow({ event, defaultExpanded = false }: EventRowProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { type, data, ts } = event;

  // For tool calls, show kwargs; for results, show output
  const renderDetails = () => {
    if (type === "ToolCall") {
      const d = data as ToolCallData;
      return (
        <div className="space-y-2">
          <div>
            <span className="text-xs font-medium text-gray-500">Arguments</span>
            <pre className="mt-1 text-xs text-gray-700 whitespace-pre-wrap break-words font-mono bg-gray-100 rounded p-2 max-h-48 overflow-auto">
              {JSON.stringify(d.tool_kwargs, null, 2)}
            </pre>
          </div>
        </div>
      );
    }

    if (type === "ToolCallResult") {
      const d = data as ToolCallResultData;
      return (
        <div className="space-y-2">
          <div>
            <span className="text-xs font-medium text-gray-500">Output</span>
            <pre className="mt-1 text-xs text-gray-700 whitespace-pre-wrap break-words font-mono bg-gray-100 rounded p-2 max-h-48 overflow-auto">
              {d.tool_output?.content || JSON.stringify(d.tool_output, null, 2)}
            </pre>
          </div>
          {d.new_report_markdown && (
            <div className="text-xs text-emerald-600 font-medium">
              ✓ Report updated
            </div>
          )}
        </div>
      );
    }

    if (type === "AgentStream") {
      const d = data as AgentStreamData;
      return (
        <div className="text-xs text-gray-700 whitespace-pre-wrap">
          {d.response || d.delta}
        </div>
      );
    }

    // Fallback: show JSON
    return (
      <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words font-mono bg-gray-100 rounded p-2 max-h-48 overflow-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <EventIcon type={type} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {formatEventTitle(event)}
          </div>
        </div>
        <div className="text-[11px] text-gray-400 tabular-nums">
          {new Date(ts).toLocaleTimeString()}
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-100 bg-gray-50">
          {renderDetails()}
        </div>
      )}
    </div>
  );
}

export function RunLog({
  events,
  emptyHint,
  autoScroll = false,
}: {
  events: FunctionAgentEvent[];
  emptyHint: string;
  /**
   * When true, the log will follow new events by scrolling to the bottom,
   * but only if the user is already near the bottom.
   */
  autoScroll?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const scrollThresholdPx = 32;

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;

    const distanceFromBottom = el.scrollHeight - (el.scrollTop + el.clientHeight);
    setStickToBottom(distanceFromBottom <= scrollThresholdPx);
  };

  const lastEventKey = useMemo(() => {
    const last = events.length > 0 ? events[events.length - 1] : undefined;
    return last ? `${last.ts}-${last.type}` : "";
  }, [events]);

  useEffect(() => {
    if (!autoScroll) return;
    if (!stickToBottom) return;
    const el = containerRef.current;
    if (!el) return;
    // Imperative, avoids smooth scrolling "catch-up" during fast streams.
    el.scrollTop = el.scrollHeight;
  }, [autoScroll, stickToBottom, lastEventKey]);

  if (events.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center">
        <div className="text-sm text-gray-600">No events yet.</div>
        <div className="text-xs text-gray-500 mt-1">{emptyHint}</div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="space-y-2 max-h-[500px] overflow-y-auto pr-1"
    >
      {events.map((ev, idx) => (
        <EventRow
          key={`${ev.ts}-${idx}`}
          event={ev}
          defaultExpanded={idx === events.length - 1}
        />
      ))}
    </div>
  );
}
