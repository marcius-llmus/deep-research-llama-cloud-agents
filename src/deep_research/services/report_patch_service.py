import tempfile
from pathlib import Path, PurePosixPath

from apply_patch_py import apply_patch
from apply_patch_py.models import AddFile, DeleteFile, UpdateFile
from apply_patch_py.parser import PatchParser


class ReportPatchService:
    def __init__(self, *, report_path: str = "artifacts/report.md") -> None:
        self.report_path = str(PurePosixPath(report_path))

    def _validate_patch(self, *, patch_text: str) -> None:
        parser = PatchParser()
        patch = parser.parse(patch_text)

        for hunk in patch.hunks:
            if isinstance(hunk, AddFile):
                raise ValueError("Patch may not add files")

            if isinstance(hunk, DeleteFile):
                raise ValueError("Patch may not delete files")

            if isinstance(hunk, UpdateFile):
                path = str(PurePosixPath(str(hunk.path)))
                if path != self.report_path:
                    raise ValueError("Patch may only target the main report")

                if hunk.move_to:
                    raise ValueError("Patch may not rename or move files")

                continue

            raise ValueError(f"Unsupported patch hunk type: {type(hunk)}")

    @staticmethod
    def _count_chunk_diff_lines(diff_text: str) -> tuple[int, int]:
        additions = 0
        deletions = 0
        for line in diff_text.splitlines():
            if line.startswith("+"):
                additions += 1
                continue
            if line.startswith("-"):
                deletions += 1
        return additions, deletions

    def _count_patch_stats(self, patch_text: str) -> tuple[int, int]:
        parser = PatchParser()
        patch = parser.parse(patch_text)


        total_additions = 0
        total_deletions = 0

        for hunk in patch.hunks:
            if isinstance(hunk, AddFile):
                total_additions += len(hunk.content.splitlines())
            elif isinstance(hunk, DeleteFile):
                pass
            elif isinstance(hunk, UpdateFile):
                for chunk in hunk.chunks:
                    chunk_additions, chunk_deletions = self._count_chunk_diff_lines(
                        chunk.diff
                    )
                    total_additions += chunk_additions
                    total_deletions += chunk_deletions

        return total_additions, total_deletions

    async def apply_patch(
        self, *, original_text: str, patch_text: str
    ) -> tuple[str, int, int]:
        patch_text = (patch_text or "").strip()

        # this is a lil bug we shall fix on the apply patch lib
        # not a bug actually, but something we can be permissive about gemini flash
        lines = patch_text.splitlines()
        if lines and lines[-1].strip() == "+":
            lines.pop()
            patch_text = "\n".join(lines)

        if not patch_text:
            raise ValueError("Patch text cannot be empty")

        self._validate_patch(patch_text=patch_text)
        additions, deletions = self._count_patch_stats(patch_text)

        with tempfile.TemporaryDirectory() as tmp_dir:
            workdir = Path(tmp_dir)
            report_path = workdir / self.report_path
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(original_text, encoding="utf-8")

            await apply_patch(patch_text, workdir=workdir)

            new_content = report_path.read_text(encoding="utf-8")
            return new_content, additions, deletions
