import { FileText, File } from "lucide-react";
import { FilePreview } from "@llamaindex/ui";

import type { ResearchArtifact } from "@/features/research/types";

const kindIcons: Record<ResearchArtifact["kind"], React.ReactNode> = {
  pdf: <FileText className="h-4 w-4" />,
  html: <File className="h-4 w-4" />,
  text: <FileText className="h-4 w-4" />,
};

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
      className={`text-left w-full rounded-lg border p-3 transition ${
        isSelected
          ? "border-gray-900 bg-gray-50 ring-1 ring-gray-900"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
      onClick={onPreview}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-gray-400">
          {kindIcons[artifact.kind] || <FileText className="h-4 w-4" />}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {artifact.name}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {artifact.kind.toUpperCase()}
            {artifact.created_at && (
              <> • {new Date(artifact.created_at).toLocaleDateString()}</>
            )}
          </div>
          {artifact.source_url && (
            <div className="mt-1.5 text-xs text-gray-500 truncate">
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
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="rounded-full bg-gray-100 p-3 mb-3">
          <FileText className="h-6 w-6 text-gray-400" />
        </div>
        <div className="text-sm font-medium text-gray-900">Mock preview</div>
        <div className="mt-1 text-xs text-gray-500 max-w-xs">
          File ID: <code className="bg-gray-100 px-1 rounded">{fileId}</code>
        </div>
      </div>
    );
  }

  return <FilePreview fileId={fileId} />;
}
