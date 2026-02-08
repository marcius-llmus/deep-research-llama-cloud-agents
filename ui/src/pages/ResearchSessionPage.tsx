import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Download, Send } from "lucide-react";
import { useHandler, useWorkflow } from "@llamaindex/ui";

import { useToolbar } from "@/lib/ToolbarContext";
import { APP_TITLE, SESSIONS_TITLE } from "@/lib/config";
import { downloadJSON } from "@/lib/export";
import { RunLog } from "@/features/research/components/RunLog";
import {
  SessionHeader,
  type SessionTabKey,
} from "@/features/research/components/SessionHeader";
import { ReportTab } from "@/features/research/components/tabs/ReportTab";
import { PlannerRunner } from "@/features/research/components/PlannerRunner";
import type { FunctionAgentEvent } from "@/features/research/events";
import { WORKFLOWS } from "@/lib/workflows";

type PageStatus = "input" | "planning" | "orchestrating" | "completed";

export default function ResearchSessionPage() {
  const { researchId } = useParams<{ researchId: string }>();
  const { setButtons, setBreadcrumbs } = useToolbar();
  
  const [status, setStatus] = useState<PageStatus>("input");
  const [query, setQuery] = useState("");
  const [plan, setPlan] = useState<string | null>(null);
  const [orchestratorHandlerId, setOrchestratorHandlerId] = useState<string | null>(null);
  const [orchestratorEvents, setOrchestratorEvents] = useState<FunctionAgentEvent[]>([]);

  const [tab, setTab] = useState<SessionTabKey>("overview");
  
  const orchestratorWorkflow = useWorkflow(WORKFLOWS.orchestrator);
  const orchestratorHandler = useHandler(orchestratorHandlerId);

  const handleExportJSON = useCallback(() => {
    downloadJSON(
      {
        query,
        plan,
        events: orchestratorEvents,
      },
      `research-${researchId || "session"}.json`,
    );
  }, [query, plan, orchestratorEvents, researchId]);

  const handleStartPlanning = () => {
    if (!query.trim()) return;
    setStatus("planning");
  };

  const handlePlannerComplete = async (planText: string) => {
    setPlan(planText);
    setStatus("orchestrating");
    
    try {
      const h = await orchestratorWorkflow.createHandler({ 
        message: `Starting research based on plan:\n${planText}` 
      });
      setOrchestratorHandlerId(h.handler_id);
    } catch (e) {
      console.error("Failed to start orchestrator", e);
    }
  };

  useEffect(() => {
    if (!orchestratorHandler || !orchestratorHandlerId) return;
    
    const sub = orchestratorHandler.subscribeToEvents({
      onData: (event) => {
        const eventName = event.type;
        let type = eventName.split('.').pop() || eventName;
        if (type === "ToolCallEvent") type = "ToolCall";
        if (type === "ToolCallResultEvent") type = "ToolCallResult";
        if (type === "AgentStreamEvent") type = "AgentStream";
        if (type === "AgentInputEvent") type = "AgentInput";
        if (type === "AgentOutputEvent") type = "AgentOutput";

        const mappedEvent: FunctionAgentEvent = {
          type: type as any,
          data: (event.data || {}),
          ts: new Date().toISOString(),
        };
        setOrchestratorEvents(prev => [...prev, mappedEvent]);
        if (eventName === "StopEvent" || eventName.endsWith("StopEvent")) {
            setStatus("completed");
        }
      }
    });
    
    return () => sub.unsubscribe();
  }, [orchestratorHandlerId]);

  useEffect(() => {
    const label = researchId || "New Session";

    setBreadcrumbs([
      { label: APP_TITLE, href: "/research" },
      { label: SESSIONS_TITLE, href: "/research" },
      { label, isCurrentPage: true },
    ]);

    setButtons(() => [
      <div key="session-actions" className="ml-auto flex items-center gap-2">
        <button
          className="inline-flex items-center gap-1.5 px-3 h-9 min-w-0 max-w-full overflow-hidden text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition"
          onClick={handleExportJSON}
        >
          <Download className="h-4 w-4 shrink-0" />
          <span className="truncate min-w-0">Export JSON</span>
        </button>
      </div>,
    ]);

    return () => {
      setButtons(() => []);
    };
  }, [researchId, handleExportJSON, setBreadcrumbs, setButtons]);

  if (status === "input") {
    return (
      <div className="p-6 flex items-center justify-center min-h-[50vh]">
        <div className="w-full max-w-2xl bg-white p-8 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Start New Research</h2>
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="What do you want to research?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStartPlanning()}
              autoFocus
            />
            <button
              onClick={handleStartPlanning}
              disabled={!query.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Start
            </button>
          </div>
          <p className="mt-4 text-sm text-gray-500">
            This will start the Planning Agent to refine your request before research begins.
          </p>
        </div>
      </div>
    );
  }

  if (status === "planning") {
    return (
      <div className="p-6 bg-gray-50 min-h-full">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-lg font-semibold mb-4 text-gray-700">Refining Research Plan</h2>
          <PlannerRunner initialQuery={query} onComplete={handlePlannerComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="max-w-6xl mx-auto space-y-4">
        <SessionHeader
          initialQuery={query}
          status={status === "completed" ? "completed" : "running"}
          updatedAt={new Date().toISOString()}
          sourcesCount={0}
          artifactsCount={0}
          tab={tab}
          setTab={setTab}
        />

        {/* Placeholder Tabs for now - logic needs to be connected to real state */}
        {tab === "overview" && <div className="p-4 bg-white rounded-lg border">Plan: <pre className="whitespace-pre-wrap text-sm">{plan}</pre></div>}
        {tab === "report" && <ReportTab reportMarkdown="# Report\n\n(Generating...)" researchId={researchId || "temp"} />}

        {(tab === "run_log" || status === "orchestrating") && (
          <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="text-sm font-semibold text-gray-900">Run log</h2>
            </div>

            <RunLog
              events={orchestratorEvents}
              emptyHint="Waiting for events..."
              autoScroll={status === "orchestrating"}
            />
          </section>
        )}
      </div>
    </div>
  );
}
