import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Download, Play } from "lucide-react";

import { useToolbar } from "@/lib/ToolbarContext";
import { APP_TITLE, SESSIONS_TITLE } from "@/lib/config";
import { downloadJSON } from "@/lib/export";
import { RunLog } from "@/features/research/components/RunLog";
import {
  SessionHeader,
  type SessionTabKey,
} from "@/features/research/components/SessionHeader";
import { FilesTab } from "@/features/research/components/tabs/FilesTab";
import { OverviewTab } from "@/features/research/components/tabs/OverviewTab";
import { ReportTab } from "@/features/research/components/tabs/ReportTab";
import { SourcesTab } from "@/features/research/components/tabs/SourcesTab";
import { getMockResearchSession } from "@/features/research/mock/sessions";
import { useMockResearchRun } from "@/features/research/hooks/useMockResearchRun";
import type { ResearchSession } from "@/features/research/types";

export default function ResearchSessionPage() {
  const { researchId } = useParams<{ researchId: string }>();
  const navigate = useNavigate();
  const { setButtons, setBreadcrumbs } = useToolbar();
  const [tab, setTab] = useState<SessionTabKey>("overview");
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(
    null,
  );

  const session = useMemo(
    () => (researchId ? getMockResearchSession(researchId) : undefined),
    [researchId],
  );

  const run = useMockResearchRun(session);
  const effectiveStatus = run.effectiveStatus ?? session?.status;
  const effectiveUpdatedAt = run.effectiveUpdatedAt ?? session?.updated_at;
  const effectiveReport = run.effectiveReport ?? session?.report_markdown;

  const handleExportJSON = useCallback(() => {
    if (!session) return;
    downloadJSON(
      {
        ...session,
        status: (effectiveStatus ?? session.status) as ResearchSession["status"],
        updated_at: effectiveUpdatedAt ?? session.updated_at,
        report_markdown: effectiveReport ?? session.report_markdown,
      },
      `research-${session.research_id}.json`,
    );
  }, [session, effectiveStatus, effectiveUpdatedAt, effectiveReport]);

  const handleStartRun = useCallback(() => {
    setTab("run_log");
    void run.start();
  }, [run]);

  const isAwaitingApproval = effectiveStatus === "awaiting_approval";

  useEffect(() => {
    if (!session) {
      setBreadcrumbs([
        { label: APP_TITLE, href: "/research" },
        { label: SESSIONS_TITLE, href: "/research" },
        { label: "Not found", isCurrentPage: true },
      ]);
      return;
    }

    setBreadcrumbs([
      { label: APP_TITLE, href: "/research" },
      { label: SESSIONS_TITLE, href: "/research" },
      { label: session.research_id, isCurrentPage: true },
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
        <button
          className="inline-flex items-center gap-1.5 px-3 h-9 min-w-0 max-w-full overflow-hidden text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleStartRun}
          disabled={run.isRunning}
        >
          <Play className="h-4 w-4 shrink-0" />
          <span className="truncate min-w-0">
            {isAwaitingApproval ? "Approve & Start" : "Start / Resume"}
          </span>
        </button>
      </div>,
    ]);

    return () => {
      setButtons(() => []);
    };
  }, [session, run.isRunning, isAwaitingApproval, handleExportJSON, handleStartRun, setBreadcrumbs, setButtons]);

  if (!session) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="text-lg font-semibold">Session not found</div>
          <div className="mt-2 text-sm text-gray-600">
            The research session you requested doesn't exist in the mock store.
          </div>
          <div className="mt-4">
            <button
              className="inline-flex items-center gap-1.5 px-3 h-9 min-w-0 max-w-full overflow-hidden text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition"
              onClick={() => navigate("/research")}
            >
              <span className="truncate min-w-0">Back to Research</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="max-w-6xl mx-auto space-y-4">
        <SessionHeader
          initialQuery={session.initial_query}
          status={effectiveStatus ?? session.status}
          updatedAt={effectiveUpdatedAt ?? session.updated_at}
          sourcesCount={session.sources.length}
          artifactsCount={session.artifacts.length}
          tab={tab}
          setTab={setTab}
        />

        {tab === "overview" && (
          <OverviewTab session={session} status={effectiveStatus ?? session.status} />
        )}

        {tab === "report" && (
          <ReportTab
            reportMarkdown={effectiveReport ?? session.report_markdown}
            researchId={session.research_id}
          />
        )}

        {tab === "sources" && <SourcesTab sources={session.sources} />}

        {tab === "files" && (
          <FilesTab
            artifacts={session.artifacts}
            selectedArtifactId={selectedArtifactId}
            setSelectedArtifactId={setSelectedArtifactId}
          />
        )}

        {tab === "run_log" && (
          <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="text-sm font-semibold text-gray-900">Run log</h2>
              <div className="text-xs text-gray-500">
                {run.events.length} events
              </div>
            </div>

            <RunLog
              events={run.events}
              emptyHint={`Click "${isAwaitingApproval ? "Approve & Start" : "Start / Resume"}" to run a mocked stream.`}
              autoScroll={run.isRunning}
            />

            <div className="mt-3 text-xs text-gray-500">
              Mock stream mirrors the real handler event contract: AgentStream,
              ToolCall, ToolCallResult, AgentInput, AgentOutput, StopEvent.
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
