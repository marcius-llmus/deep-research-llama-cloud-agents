import { Download } from "lucide-react";

import { MarkdownPreview } from "@/features/research/components/MarkdownPreview";

export function ReportTab({
  reportMarkdown,
  researchId,
}: {
  reportMarkdown: string;
  researchId: string;
}) {
  const handleExport = () => {
    const blob = new Blob([reportMarkdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research-${researchId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-gray-900">Live report</h2>
        <button
          className="inline-flex items-center gap-1.5 px-3 h-9 min-w-0 max-w-full overflow-hidden text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition"
          onClick={handleExport}
        >
          <Download className="h-4 w-4 shrink-0" />
          <span className="truncate min-w-0">Export Markdown</span>
        </button>
      </div>

      <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4 max-h-[500px] overflow-y-auto">
        {reportMarkdown ? (
          <MarkdownPreview value={reportMarkdown} />
        ) : (
          <div className="text-sm text-gray-500 italic">
            No report content yet. Start the research to generate the report.
          </div>
        )}
      </div>

      <div className="mt-3 text-xs text-gray-500">
        During an active run, the authoritative report lives in agent context
        and updates via <code className="bg-gray-100 px-1 rounded">ToolCallResult(update_report)</code>.
      </div>
    </section>
  );
}
