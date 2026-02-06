import { useCallback, useMemo, useRef, useState } from "react";

import type { FunctionAgentEvent } from "@/features/research/events";
import type { ResearchSession, ResearchStatus } from "@/features/research/types";
import { streamMockResearchRun } from "@/features/research/mock/stream";

export function useMockResearchRun(session: ResearchSession | undefined) {
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<FunctionAgentEvent[]>([]);
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const runIdRef = useRef(0);

  const effectiveStatus = status ?? session?.status;
  const effectiveUpdatedAt = updatedAt ?? session?.updated_at;
  const effectiveReport = reportMarkdown ?? session?.report_markdown;

  const start = useCallback(async () => {
    if (!session || isRunning) return;

    // invalidate any previous run loops
    runIdRef.current += 1;
    const runId = runIdRef.current;

    setIsRunning(true);
    setEvents([]);
    setReportMarkdown(session.report_markdown);
    setStatus("running");
    setUpdatedAt(new Date().toISOString());

    try {
      for await (const ev of streamMockResearchRun(session)) {
        if (runId !== runIdRef.current) {
          // new run started; abort this one
          return;
        }

        setEvents((prev) => [...prev, ev]);

        if (
          ev.type === "ToolCallResult" &&
          ev.data.tool_name === "update_report" &&
          typeof ev.data.new_report_markdown === "string"
        ) {
          setReportMarkdown(ev.data.new_report_markdown);
          setUpdatedAt(new Date().toISOString());
        }

        if (ev.type === "StopEvent") {
          setStatus("completed");
          setUpdatedAt(new Date().toISOString());
        }
      }
    } finally {
      setIsRunning(false);
    }
  }, [isRunning, session]);

  return useMemo(
    () => ({
      isRunning,
      events,
      effectiveReport,
      effectiveStatus,
      effectiveUpdatedAt,
      start,
    }),
    [
      effectiveReport,
      effectiveStatus,
      effectiveUpdatedAt,
      events,
      isRunning,
      start,
    ],
  );
}

