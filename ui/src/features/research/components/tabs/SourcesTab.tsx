import { ExternalLink } from "lucide-react";

import type { ResearchSource } from "@/features/research/types";

export function SourcesTab({ sources }: { sources: ResearchSource[] }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-900">Sources</h2>
      <div className="mt-4 space-y-3">
        {sources.map((src, idx) => (
          <div key={idx} className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="font-medium text-gray-900 truncate">
                  {src.title ?? src.url}
                </div>
                <div className="mt-1 text-xs text-gray-500 truncate">{src.url}</div>
                {src.snippet && (
                  <div className="mt-2 text-sm text-gray-700">{src.snippet}</div>
                )}
                {src.notes && (
                  <div className="mt-3 text-xs text-gray-600 whitespace-pre-wrap">
                    {src.notes}
                  </div>
                )}
              </div>
              <a
                className="shrink-0 inline-flex items-center gap-1 text-xs text-gray-700 hover:text-gray-900"
                href={src.url}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="h-4 w-4" />
                Open
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

