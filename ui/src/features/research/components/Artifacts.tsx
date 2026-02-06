import { FileText } from "lucide-react";
import { FilePreview } from "@llamaindex/ui";

import type { ResearchArtifact } from "@/features/research/types";

export function ArtifactCard({
  artifact,
  onPreview,
  isSelected,
}: {
  artifact: ResearchArtifact;
  onPreview: () => void;
  isSelected: boolean;
}) {
  return (
    <button
      className={`text-left w-full rounded-xl border p-3 transition ${
        isSelected
          ? "border-gray-900 bg-gray-50"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
      onClick={onPreview}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-gray-500">
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="font-medium text-gray-900 truncate">
            {artifact.name}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {artifact.kind.toUpperCase()} • {artifact.file_id}
          </div>
          {artifact.source_url && (
            <div className="mt-2 text-xs text-gray-600 truncate">
              {artifact.source_url}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

export function MockFilePreview({ fileId }: { fileId: string }) {
  if (fileId.startsWith("file_mock_")) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center">
          <div className="text-sm font-medium text-gray-900">
            Mock artifact preview
          </div>
          <div className="mt-2 text-xs text-gray-500">
            This is a mocked file_id ({fileId}). In the real workflow, this would
            be a Llama Cloud File ID and would preview here.
          </div>
        </div>
      </div>
    );
  }

  return <FilePreview fileId={fileId} />;
}
