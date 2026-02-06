import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@llamaindex/ui";
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
      <div key="research-actions" className="ml-auto flex items-center gap-2">
        <Button
          onClick={() => {
            // Mock: go to the first session detail (in a real version this would create a new session)
            const first = sessions[0];
            if (first) {
              navigate(`/research/${first.research_id}`);
            }
          }}
        >
          <Plus className="h-4 w-4 mr-2" />
          New research
        </Button>
      </div>,
    ]);

    return () => {
      setButtons(() => []);
    };
  }, [navigate, sessions, setBreadcrumbs, setButtons]);

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="max-w-6xl mx-auto space-y-6">
        <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold">{APP_TITLE}</h1>
              <p className="text-sm text-gray-500 mt-1">
                Plan first. After approval, the agent runs web research and updates the
                report live.
              </p>
            </div>
            <div className="w-full max-w-md">
              <label className="text-xs text-gray-500">Search sessions</label>
              <div className="mt-1 flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2">
                <Search className="h-4 w-4 text-gray-400" />
                <input
                  className="w-full text-sm outline-none"
                  placeholder="Type keywords..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-3">
            {filtered.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center">
                <div className="text-sm text-gray-600">No sessions found.</div>
                <div className="text-xs text-gray-500 mt-1">
                  Try a different query or create a new research session.
                </div>
              </div>
            ) : (
              filtered.map((s) => (
                <button
                  key={s.research_id}
                  className="group text-left rounded-xl border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm transition"
                  onClick={() => navigate(`/research/${s.research_id}`)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
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
                    <div className="shrink-0 text-gray-400 group-hover:text-gray-700">
                      <ArrowRight className="h-4 w-4" />
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
