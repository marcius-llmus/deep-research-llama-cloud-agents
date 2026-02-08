import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search, ArrowRight } from "lucide-react";

import { useToolbar } from "@/lib/ToolbarContext";
import { APP_TITLE, SESSIONS_TITLE } from "@/lib/config";

export default function ResearchPage() {
  const navigate = useNavigate();
  const { setButtons, setBreadcrumbs } = useToolbar();

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
            // Generate a random ID for the new session
            const newId = crypto.randomUUID();
            navigate(`/research/${newId}`);
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
  }, [navigate, setBreadcrumbs, setButtons]);

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
              {/* Search removed as we don't have persistence yet */}
            </div>
          </div>
        </section>

        {/* Sessions list */}
        <section className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center">
          <div className="text-sm text-gray-600">No sessions found (Persistence not implemented).</div>
          <div className="text-xs text-gray-500 mt-1">
            Click "New research" to start a new session.
          </div>
        </section>
      </div>
    </div>
  );
}
