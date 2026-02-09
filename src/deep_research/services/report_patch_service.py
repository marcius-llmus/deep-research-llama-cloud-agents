from __future__ import annotations


class ReportPatchService:
    """Applies patch text to a report."""

    def apply_patch_mock(self, *, original_text: str, patch_text: str) -> str:
        patch_text = (patch_text or "").strip()
        if not patch_text:
            return original_text

        return (
            original_text.rstrip()
            + "\n\n<!-- PATCH_APPLIED_MOCK -->\n"
            + patch_text
            + "\n"
        )
