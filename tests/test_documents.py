from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_chunk_text_empty_returns_empty():
    from apps.core.documents import chunk_text
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []


def test_chunk_text_short_text_one_chunk():
    from apps.core.documents import chunk_text
    text = "Hello world."
    result = chunk_text(text, size=100, overlap=20)
    assert len(result) == 1
    assert result[0] == "Hello world."


def test_chunk_text_long_text_overlapping_chunks():
    from apps.core.documents import chunk_text
    text = ". ".join(["sentence"] * 200)
    result = chunk_text(text, size=500, overlap=50)
    assert len(result) > 1


def test_chunk_text_break_at_sentence_boundary():
    from apps.core.documents import chunk_text
    text = "First short sentence. Second sentence that runs on. Third here."
    result = chunk_text(text, size=40, overlap=5)
    for chunk in result:
        assert "sentence" in chunk.lower() or "third" in chunk.lower()


def test_ingest_text_creates_document_and_chunks(doc_db):
    from apps.core import documents
    text = ". ".join(["content"] * 50)
    result = documents.ingest_text(name="test.txt", source="unit test", text=text)
    assert "doc_id" in result
    assert result["name"] == "test.txt"
    assert result["chunks"] >= 1
    assert result["total_chars"] == len(text)


def test_list_documents(doc_db):
    from apps.core import documents
    documents.ingest_text("a.txt", "src1", "alpha content " * 100)
    documents.ingest_text("b.txt", "src2", "beta content " * 100)
    docs = documents.list_documents()
    assert len(docs) == 2
    names = {d["name"] for d in docs}
    assert names == {"a.txt", "b.txt"}


def test_get_doc_count(doc_db):
    from apps.core import documents
    assert documents.get_doc_count() == 0
    documents.ingest_text("x.txt", "src", "stuff " * 50)
    assert documents.get_doc_count() == 1


def test_search_chunks_finds_match(doc_db):
    from apps.core import documents
    documents.ingest_text(
        "kb.txt",
        "src",
        "The capital of France is Paris. Paris has the Eiffel Tower.",
    )
    docs = documents.search_chunks("Eiffel", limit=5)
    assert len(docs) >= 1
    assert any("Eiffel" in d["content"] for d in docs)


def test_search_chunks_returns_metadata(doc_db):
    from apps.core import documents
    documents.ingest_text("doc.txt", "src", "alpha pattern alpha here.")
    docs = documents.search_chunks("alpha", limit=10)
    for d in docs:
        assert "name" in d
        assert "doc_id" in d
        assert "idx" in d
        assert "content" in d


def test_search_chunks_filter_by_doc_ids(doc_db):
    from apps.core import documents
    r1 = documents.ingest_text("doc1.txt", "src", "keyword_one appears here.")
    r2 = documents.ingest_text("doc2.txt", "src", "keyword_one appears there.")
    docs_all = documents.search_chunks("keyword_one", limit=10)
    docs_filtered = documents.search_chunks("keyword_one", limit=10, doc_ids=[r1["doc_id"]])
    assert len(docs_all) >= 2
    assert len(docs_filtered) == 1
    assert docs_filtered[0]["name"] == "doc1.txt"


def test_get_document_chunks_in_order(doc_db):
    from apps.core import documents
    long_text = ". ".join([f"section{i}" for i in range(20)])
    r = documents.ingest_text("ordered.txt", "src", long_text)
    chunks = documents.get_document_chunks(r["doc_id"])
    for i, c in enumerate(chunks):
        assert c["idx"] == i


def test_delete_document(doc_db):
    from apps.core import documents
    r = documents.ingest_text("tmp.txt", "src", "to be deleted.")
    doc_id = r["doc_id"]
    assert documents.get_doc_count() == 1
    assert documents.delete_document(doc_id) is True
    assert documents.get_doc_count() == 0
    assert documents.delete_document(doc_id) is False


def test_format_rag_context_empty():
    from apps.core.documents import format_rag_context
    assert format_rag_context([]) == ""


def test_format_rag_context_includes_source(doc_db):
    from apps.core import documents
    documents.ingest_text("source-name.txt", "src", "some content here.")
    results = documents.search_chunks("content", limit=5)
    ctx = documents.format_rag_context(results)
    assert "source-name.txt" in ctx
    assert "some content here" in ctx


def test_format_rag_context_respects_budget(doc_db):
    from apps.core import documents
    big = "x" * 100 + ". " + "y" * 100 + ". " + "z" * 100
    documents.ingest_text("big.txt", "src", big)
    results = documents.search_chunks("x", limit=5)
    ctx = documents.format_rag_context(results, max_chars=50)
    assert len(ctx) <= 200
