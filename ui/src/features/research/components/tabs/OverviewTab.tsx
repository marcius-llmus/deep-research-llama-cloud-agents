import { Clock } from "lucide-react";

import type { ResearchSession } from "@/features/research/types";
import { StatusPill } from "@/features/research/components/StatusPill";

function PlanSection({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (items.length === 0) {
    return (
      <div>
        <div className="text-xs font-medium text-gray-500">{title}</div>
        <div className="mt-2 text-sm text-gray-400 italic">None</div>
      </div>
    );
  }

  return (
    <div>
      <div className="text-xs font-medium text-gray-500">{title}</div>
      <ul className="mt-2 list-disc pl-5 text-sm text-gray-800 space-y-1">
        {items.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function OverviewTab({
  session,
  status,
}: {
  session: ResearchSession;
  status: ResearchSession["status"];
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Plan panel - scrollable */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Plan</h2>
          <div className="max-h-[400px] overflow-y-auto pr-2 space-y-4 rounded-lg border border-gray-100 bg-gray-50 p-4">
            <PlanSection
              title="Clarifying questions"
              items={session.plan.clarifying_questions}
            />
            <PlanSection
              title="Expanded queries"
              items={session.plan.expanded_queries}
            />
            <PlanSection title="Outline" items={session.plan.outline} />
          </div>
        </div>

        {/* Session info panel */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Session</h2>
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
            <div>
              <div className="text-xs font-medium text-gray-500">Status</div>
              <div className="mt-1.5">
                <StatusPill status={status} />
              </div>
            </div>

            <div>
              <div className="text-xs font-medium text-gray-500">Created</div>
              <div className="mt-1.5 flex items-center gap-1.5 text-sm text-gray-700">
                <Clock className="h-3.5 w-3.5 text-gray-400" />
                {new Date(session.created_at).toLocaleString()}
              </div>
            </div>

            <div>
              <div className="text-xs font-medium text-gray-500">Research ID</div>
              <div className="mt-1.5 text-xs font-mono text-gray-600 bg-gray-50 rounded px-2 py-1 break-all">
                {session.research_id}
              </div>
            </div>

            <div>
              <div className="text-xs font-medium text-gray-500">Initial query</div>
              <div className="mt-1.5 text-sm text-gray-700">{session.initial_query}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
