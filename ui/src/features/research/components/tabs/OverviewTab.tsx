import { Clock } from "lucide-react";

import type { ResearchSession } from "@/features/research/types";
import { StatusPill } from "@/features/research/components/StatusPill";

export function OverviewTab({
  session,
  status,
}: {
  session: ResearchSession;
  status: ResearchSession["status"];
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-900">Plan</h2>
          <div className="mt-3 space-y-4">
            <div>
              <div className="text-xs font-medium text-gray-500">
                Clarifying questions
              </div>
              <ul className="mt-2 list-disc pl-5 text-sm text-gray-800 space-y-1">
                {session.plan.clarifying_questions.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-medium text-gray-500">
                Expanded queries
              </div>
              <ul className="mt-2 list-disc pl-5 text-sm text-gray-800 space-y-1">
                {session.plan.expanded_queries.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-medium text-gray-500">Outline</div>
              <ul className="mt-2 list-disc pl-5 text-sm text-gray-800 space-y-1">
                {session.plan.outline.map((o, idx) => (
                  <li key={idx}>{o}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-gray-900">Session</h2>
          <div className="mt-3 rounded-lg border border-gray-200 p-3">
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <Clock className="h-4 w-4" />
              <span>Created {new Date(session.created_at).toLocaleString()}</span>
            </div>
            <div className="mt-3 text-xs text-gray-600">
              <div className="font-medium text-gray-900">research_id</div>
              <div className="mt-1 font-mono break-all">{session.research_id}</div>
            </div>
            <div className="mt-3 text-xs text-gray-600">
              <div className="font-medium text-gray-900">Status</div>
              <div className="mt-1">
                <StatusPill status={status} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

