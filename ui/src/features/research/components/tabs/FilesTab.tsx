import type { ResearchArtifact } from "@/features/research/types";
import { ArtifactCard, MockFilePreview } from "@/features/research/components/Artifacts";

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

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-gray-900">Files</h2>
        <div className="text-xs text-gray-500">
          Preview uses Llama Cloud File IDs (mocked IDs won't load).
        </div>
      </div>

      {artifacts.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-gray-200 p-6 text-center">
          <div className="text-sm text-gray-600">No artifacts saved.</div>
          <div className="text-xs text-gray-500 mt-1">
            In the real workflow, fetched documents can be stored as Llama Cloud
            Files and listed here.
          </div>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-2 space-y-2">
            {artifacts.map((a) => (
              <ArtifactCard
                key={a.file_id}
                artifact={a}
                onPreview={() => setSelectedArtifactId(a.file_id)}
                isSelected={selectedArtifact?.file_id === a.file_id}
              />
            ))}
          </div>
          <div className="lg:col-span-3 rounded-xl border border-gray-200 bg-white overflow-hidden">
            {selectedArtifact?.file_id ? (
              <MockFilePreview fileId={selectedArtifact.file_id} />
            ) : (
              <div className="p-6 text-sm text-gray-600">
                Select an artifact to preview.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
