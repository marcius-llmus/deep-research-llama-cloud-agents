from deep_research.services.models import ParsedDocument


class DocumentParserService:
    """Fetches + parses documents into clean text.

    For now this is a MOCK implementation:
    - PDF/CSV parsing is stubbed.
    - HTML parsing is expected to be done by the caller (e.g., OxylabsWebReader).

    Later, this can be swapped to real parsing (PDF text extraction, CSV summarization,
    chart/image OCR, etc.).
    """



    def classify(self, source: str) -> str:
        lowered = (source or "").lower()
        if lowered.endswith(".pdf"):
            return "pdf"
        if lowered.endswith(".csv"):
            return "csv"
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return "html"
        return "unknown"

    async def parse_stub(self, *, source: str, text: str | None = None) -> ParsedDocument:
        content_type = self.classify(source)
        if content_type == "pdf":
            return ParsedDocument(
                source=source,
                content_type="pdf",
                text=text
                or (
                    "[MOCK PDF PARSE]\n"
                    "PDF parsing is not implemented yet. Replace DocumentParserService.parse_stub with a real parser.\n"
                    f"Source: {source}\n"
                ),
                parse_notes="mock_pdf_parse",
            )

        if content_type == "csv":
            return ParsedDocument(
                source=source,
                content_type="csv",
                text=text
                or (
                    "[MOCK CSV PARSE]\n"
                    "CSV parsing is not implemented yet. Replace DocumentParserService.parse_stub with a real parser.\n"
                    f"Source: {source}\n"
                ),
                parse_notes="mock_csv_parse",
            )

        return ParsedDocument(
            source=source,
            content_type=content_type,
            text=text or "",
        )
