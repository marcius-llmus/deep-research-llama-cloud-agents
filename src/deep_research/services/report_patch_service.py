import tempfile
from pathlib import Path, PurePosixPath

from apply_patch_py import apply_patch
from apply_patch_py.models import AddFile, DeleteFile, UpdateFile
from apply_patch_py.parser import PatchParser
from workflows import Context

from deep_research.workflows.research.state_keys import ReportStateKey, StateNamespace


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

    async def apply_patch(self, *, ctx: Context, patch_text: str) -> str:
        patch_text = (patch_text or "").strip()

        state = await ctx.store.get_state()
        original_text = state[StateNamespace.REPORT][ReportStateKey.CONTENT]

        if not patch_text:
            return original_text

        self._validate_patch(patch_text=patch_text)

        with tempfile.TemporaryDirectory() as tmp_dir:
            workdir = Path(tmp_dir)
            report_path = workdir / self.report_path
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(original_text, encoding="utf-8")

            await apply_patch(patch_text, workdir=workdir)
            return report_path.read_text(encoding="utf-8")
