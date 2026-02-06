import type { ResearchArtifact } from "@/features/research/types";
import {
  ArtifactCard,
  MockFilePreview,
} from "@/features/research/components/Artifacts";

export function FilesTab({
  artifacts,
  selectedArtifactId,
  setSelectedArtifactId,
}: {
  artifacts: ResearchArtifact[];
  selectedArtifactId: string | null;
  setSelectedArtifactId: (fileId: string) => void;
}) {
  const selectedArtifact =
    selectedArtifactId != null
      ? artifacts.find((a) => a.file_id === selectedArtifactId)
      : artifacts[0];

  if (artifacts.length === 0) {
    return (
      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">Files</h2>
        <div className="mt-4 rounded-lg border border-dashed border-gray-200 p-6 text-center">
          <div className="text-sm text-gray-600">No files saved.</div>
          <div className="text-xs text-gray-500 mt-1">
            When the workflow fetches documents, they can be stored as Llama
            Cloud Files and previewed here.
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-sm font-semibold text-gray-900">Files</h2>
        <div className="text-xs text-gray-500">{artifacts.length} files</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* File list - scrollable */}
        <div className="lg:col-span-2 space-y-2 max-h-[400px] overflow-y-auto pr-1">
          {artifacts.map((a) => (
            <ArtifactCard
              key={a.file_id}
              artifact={a}
              onPreview={() => setSelectedArtifactId(a.file_id)}
              isSelected={selectedArtifact?.file_id === a.file_id}
            />
          ))}
        </div>

        {/* Preview panel */}
        <div className="lg:col-span-3 rounded-lg border border-gray-200 bg-gray-50 overflow-hidden min-h-[300px] flex flex-col">
          {selectedArtifact?.file_id ? (
            <MockFilePreview fileId={selectedArtifact.file_id} />
          ) : (
            <div className="flex-1 flex items-center justify-center p-6 text-sm text-gray-500">
              Select a file to preview.
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 text-xs text-gray-500">
        Preview uses Llama Cloud File IDs. Mocked IDs show a placeholder.
      </div>
    </section>
  );
}
