import { ExternalLink } from "lucide-react";

import type { ResearchSource } from "@/features/research/types";

export function SourcesTab({ sources }: { sources: ResearchSource[] }) {
  if (sources.length === 0) {
    return (
      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">Sources</h2>
        <div className="mt-4 rounded-lg border border-dashed border-gray-200 p-6 text-center">
          <div className="text-sm text-gray-600">No sources collected yet.</div>
          <div className="text-xs text-gray-500 mt-1">
            Sources will appear here as the agent retrieves them during research.
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-sm font-semibold text-gray-900">Sources</h2>
        <div className="text-xs text-gray-500">{sources.length} sources</div>
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {sources.map((src, idx) => {
          const domain = (() => {
            try {
              return new URL(src.url).hostname.replace("www.", "");
            } catch {
              return src.url;
            }
          })();

          return (
            <div key={idx} className="rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 transition">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-gray-900 line-clamp-2">
                    {src.title || domain}
                  </div>
                  <div className="mt-1 text-xs text-gray-500 truncate">{src.url}</div>
                  {src.snippet && (
                    <div className="mt-2 text-sm text-gray-600 line-clamp-3">{src.snippet}</div>
                  )}
                  {src.notes && (
                    <div className="mt-3 text-xs text-gray-600 bg-gray-50 rounded p-2 whitespace-pre-wrap max-h-24 overflow-y-auto">
                      {src.notes}
                    </div>
                  )}
                </div>
                <a
                  className="shrink-0 inline-flex items-center gap-1.5 px-2.5 h-8 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition"
                  href={src.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Open
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
