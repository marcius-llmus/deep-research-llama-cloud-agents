import type { FunctionAgentEvent } from "@/features/research/events";

export function RunLog({
  events,
  emptyHint,
}: {
  events: FunctionAgentEvent[];
  emptyHint: string;
}) {
  if (events.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-gray-200 p-6 text-center">
        <div className="text-sm text-gray-600">No events yet.</div>
        <div className="text-xs text-gray-500 mt-1">{emptyHint}</div>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-2">
      {events.map((ev, idx) => (
        <div
          key={`${ev.ts}-${idx}`}
          className="rounded-lg border border-gray-200 bg-gray-50 p-3"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-gray-500">{ev.type}</div>
            <div className="text-[11px] text-gray-400">
              {new Date(ev.ts).toLocaleTimeString()}
            </div>
          </div>
          <pre className="mt-2 text-xs text-gray-800 whitespace-pre-wrap break-words font-mono">
            {JSON.stringify(ev.data, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}
