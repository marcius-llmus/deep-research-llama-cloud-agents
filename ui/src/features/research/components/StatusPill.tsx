import type { ResearchStatus } from "@/features/research/types";

export function StatusPill({ status }: { status: ResearchStatus }) {
  const styles: Record<ResearchStatus, string> = {
    planning: "bg-blue-50 text-blue-700 border-blue-200",
    awaiting_approval: "bg-amber-50 text-amber-700 border-amber-200",
    running: "bg-purple-50 text-purple-700 border-purple-200",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    failed: "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        styles[status]
      }`}
    >
      {status.split("_").join(" ")}
    </span>
  );
}

