import { Button } from "@llamaindex/ui";
import { Download } from "lucide-react";

import { MarkdownPreview } from "@/features/research/components/MarkdownPreview";

export function ReportTab({
  reportMarkdown,
  researchId,
}: {
  reportMarkdown: string;
  researchId: string;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-gray-900">Live report</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const blob = new Blob([reportMarkdown], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `research-${researchId}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          }}
        >
          <Download className="h-4 w-4 mr-2" />
          Export Markdown
        </Button>
      </div>

      <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <MarkdownPreview value={reportMarkdown} />
      </div>

      <div className="mt-3 text-xs text-gray-500">
        During an active run, the authoritative report lives in agent context and
        updates come from ToolCallResult(update_report).
      </div>
    </section>
  );
}

