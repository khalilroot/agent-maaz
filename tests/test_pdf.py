from __future__ import annotations

import tempfile
from pathlib import Path


def _make_pdf(tmp: Path, name: str, pages: list[str]) -> Path:
    from reportlab.pdfgen import canvas
    p = tmp / name
    c = canvas.Canvas(str(p))
    for text in pages:
        c.drawString(100, 700, text)
        c.showPage()
    c.save()
    return p


def test_ingest_pdf_reads_text(doc_db):
    from apps.core import documents
    with tempfile.TemporaryDirectory() as d:
        pdf_path = _make_pdf(
            Path(d), "test.pdf", ["Hello world from PDF.", "Second page here."]
        )
        result = documents.ingest_file(str(pdf_path))
        assert result["doc_id"] > 0
        chunks = documents.get_document_chunks(result["doc_id"])
        joined = "".join(c["content"] for c in chunks)
        assert len(joined) > 0
        assert "PDF" in joined or "Hello" in joined


def test_ingest_pdf_missing_file(doc_db):
    from apps.core import documents
    import pytest
    with pytest.raises(FileNotFoundError):
        documents.ingest_file("/no/such/file.pdf")
