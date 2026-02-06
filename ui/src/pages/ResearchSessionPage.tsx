import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@llamaindex/ui";
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
      <div key="research-session-actions" className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
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
          }}
        >
          <Download className="h-4 w-4 mr-2" />
          Export JSON
        </Button>
        <Button
          size="sm"
          onClick={() => {
            // Mock: in real UI this would send an approval event or start the execute run
            setTab("run_log");
            void run.start();
          }}
          disabled={run.isRunning}
        >
          <Play className="h-4 w-4 mr-2" />
          {effectiveStatus === "awaiting_approval"
            ? "Approve & Start"
            : "Start / Resume"}
        </Button>
      </div>,
    ]);

    return () => {
      setButtons(() => []);
    };
  }, [
    effectiveReport,
    effectiveStatus,
    effectiveUpdatedAt,
    run.isRunning,
    session,
    setBreadcrumbs,
    setButtons,
    run,
  ]);

  if (!session) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="text-lg font-semibold">Session not found</div>
          <div className="mt-2 text-sm text-gray-600">
            The research session you requested doesn’t exist in the mock store.
          </div>
          <div className="mt-4">
            <Button variant="outline" onClick={() => navigate("/research")}>
              Back to Research
            </Button>
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

        {tab === "sources" && (
          <SourcesTab sources={session.sources} />
        )}

        {tab === "files" && (
          <FilesTab
            artifacts={session.artifacts}
            selectedArtifactId={selectedArtifactId}
            setSelectedArtifactId={setSelectedArtifactId}
          />
        )}

        {tab === "run_log" && (
          <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900">Run log</h2>
            <div className="mt-2 text-xs text-gray-500">
              Mock stream. This mirrors the real handler event stream contract
              (AgentStream, ToolCall, ToolCallResult, AgentInput, AgentOutput,
              StopEvent, WorkflowCancelledEvent).
            </div>

            <RunLog
              events={run.events}
              emptyHint={`Click “${
                effectiveStatus === "awaiting_approval" ? "Approve & Start" : "Start / Resume"
              }” to run a mocked stream.`}
            />
          </section>
        )}
      </div>
    </div>
  );
}
