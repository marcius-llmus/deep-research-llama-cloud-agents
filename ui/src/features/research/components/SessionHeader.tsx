import type { ResearchStatus } from "@/features/research/types";
import { StatusPill } from "@/features/research/components/StatusPill";
import { TabButton } from "@/features/research/components/Tabs";

export type SessionTabKey = "overview" | "report" | "sources" | "files" | "run_log";

export function SessionHeader({
  initialQuery,
  status,
  updatedAt,
  sourcesCount,
  artifactsCount,
  tab,
  setTab,
}: {
  initialQuery: string;
  status: ResearchStatus;
  updatedAt: string;
  sourcesCount: number;
  artifactsCount: number;
  tab: SessionTabKey;
  setTab: (tab: SessionTabKey) => void;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <StatusPill status={status} />
            <span className="text-xs text-gray-500">
              updated {new Date(updatedAt).toLocaleString()}
            </span>
          </div>
          <h1 className="mt-3 text-lg font-semibold text-gray-900">
            {initialQuery}
          </h1>
          <div className="mt-2 text-xs text-gray-500">
            {sourcesCount} sources • {artifactsCount} files
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2">
          <TabButton
            label="Overview"
            active={tab === "overview"}
            onClick={() => setTab("overview")}
          />
          <TabButton
            label="Live report"
            active={tab === "report"}
            onClick={() => setTab("report")}
          />
          <TabButton
            label="Sources"
            active={tab === "sources"}
            onClick={() => setTab("sources")}
          />
          <TabButton
            label="Files"
            active={tab === "files"}
            onClick={() => setTab("files")}
          />
          <TabButton
            label="Run log"
            active={tab === "run_log"}
            onClick={() => setTab("run_log")}
          />
        </div>
      </div>

      {/* Mobile tab row */}
      <div className="mt-4 flex md:hidden flex-wrap gap-2">
        <TabButton
          label="Overview"
          active={tab === "overview"}
          onClick={() => setTab("overview")}
        />
        <TabButton
          label="Live report"
          active={tab === "report"}
          onClick={() => setTab("report")}
        />
        <TabButton
          label="Sources"
          active={tab === "sources"}
          onClick={() => setTab("sources")}
        />
        <TabButton
          label="Files"
          active={tab === "files"}
          onClick={() => setTab("files")}
        />
        <TabButton
          label="Run log"
          active={tab === "run_log"}
          onClick={() => setTab("run_log")}
        />
      </div>
    </section>
  );
}
