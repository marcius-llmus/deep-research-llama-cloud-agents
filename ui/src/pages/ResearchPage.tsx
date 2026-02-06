import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search, ArrowRight } from "lucide-react";

import { useToolbar } from "@/lib/ToolbarContext";
import { APP_TITLE, SESSIONS_TITLE } from "@/lib/config";
import { listMockResearchSessions } from "@/features/research/mock/sessions";
import type { ResearchSession } from "@/features/research/types";
import { StatusPill } from "@/features/research/components/StatusPill";

export default function ResearchPage() {
  const navigate = useNavigate();
  const { setButtons, setBreadcrumbs } = useToolbar();

  const sessions = useMemo(() => listMockResearchSessions(), []);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) => s.initial_query.toLowerCase().includes(q));
  }, [query, sessions]);

  useEffect(() => {
    setBreadcrumbs([
      { label: APP_TITLE, href: "/research" },
      { label: SESSIONS_TITLE, isCurrentPage: true },
    ]);

    setButtons(() => [
      <div key="page-actions" className="ml-auto flex items-center gap-2">
        <button
          className="inline-flex items-center gap-1.5 px-3 h-9 min-w-0 max-w-full overflow-hidden text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition"
          onClick={() => {
            const first = sessions[0];
            if (first) {
              navigate(`/research/${first.research_id}`);
            }
          }}
        >
          <Plus className="h-4 w-4 shrink-0" />
          <span className="truncate min-w-0">New research</span>
        </button>
      </div>,
    ]);

    return () => {
      setButtons(() => []);
    };
  }, [navigate, sessions, setBreadcrumbs, setButtons]);

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header card */}
        <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{APP_TITLE}</h1>
              <p className="text-sm text-gray-500 mt-1">
                Plan first. After approval, the agent runs web research and
                updates the report live.
              </p>
            </div>
            <div className="w-full md:w-72 shrink-0">
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 h-9">
                <Search className="h-4 w-4 text-gray-400 shrink-0" />
                <input
                  className="w-full text-sm outline-none bg-transparent"
                  placeholder="Search sessions..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Sessions list */}
        {filtered.length === 0 ? (
          <section className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center">
            <div className="text-sm text-gray-600">No sessions found.</div>
            <div className="text-xs text-gray-500 mt-1">
              {query
                ? "Try a different search term."
                : 'Click "New research" to start your first session.'}
            </div>
          </section>
        ) : (
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Sessions
              </div>
              <div className="text-xs text-gray-500">
                {filtered.length} of {sessions.length}
              </div>
            </div>

            {filtered.map((s) => (
              <button
                key={s.research_id}
                className="w-full group text-left rounded-xl border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm transition"
                onClick={() => navigate(`/research/${s.research_id}`)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <StatusPill status={s.status} />
                      <span className="text-xs text-gray-500">
                        updated {new Date(s.updated_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-2 font-medium text-gray-900 line-clamp-2">
                      {s.initial_query}
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      {s.sources.length} sources • {s.artifacts.length} files
                    </div>
                  </div>
                  <div className="shrink-0 text-gray-400 group-hover:text-gray-700 transition">
                    <ArrowRight className="h-4 w-4" />
                  </div>
                </div>
              </button>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
