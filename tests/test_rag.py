from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def bootstrap():
    from eval_type_backport import eval_type_backport  # noqa: F401


def _make_chat_returning(content: str):
    """Returns a fake _call_model that produces plain text on first call."""
    from apps.core import router

    def fake_call(client, model, msgs, stream, tools=None):
        from tests.test_function_calling import _response_with, _message
        return _response_with(_message(content))

    return fake_call


def test_chat_with_rag_no_documents_falls_through(monkeypatch, fake_openai_key, temp_db):
    from apps.core import router

    monkeypatch.setattr(router, "_call_model", _make_chat_returning("just a hello"))
    sid = router.new_session()
    reply, tool_log, rag_context = router.chat_with_rag(sid, "hi")
    assert reply == "just a hello"
    assert rag_context == ""


def test_chat_with_rag_injects_context(monkeypatch, fake_openai_key, temp_db, doc_db):
    from apps.core import router
    from apps.core import documents

    documents.ingest_text(
        "kb.txt", "src", "The capital of Egypt is Cairo. Cairo has pyramids."
    )

    captured_msgs = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured_msgs.append(list(msgs))
        from tests.test_function_calling import _response_with, _message
        return _response_with(_message("I see the context"))

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    reply, tool_log, rag_context = router.chat_with_rag(sid, "what is the capital?")

    assert "kb.txt" in rag_context
    assert "Cairo" in rag_context
    assert reply == "I see the context"

    user_msg = captured_msgs[0][-1]
    assert isinstance(user_msg, dict)
    assert "Cairo" in user_msg["content"] or "capital" in user_msg["content"].lower()


def test_chat_with_rag_persists_user_message(monkeypatch, fake_openai_key, temp_db):
    from apps.core import router
    from apps.core import memory

    monkeypatch.setattr(router, "_call_model", _make_chat_returning("OK"))
    sid = router.new_session()
    router.chat_with_rag(sid, "remember this")
    rows = memory.get_messages(sid)
    saved_user = next(r for r in rows if r["role"] == "user")
    assert "remember this" in saved_user["content"]


def test_chat_with_rag_passes_doc_ids(monkeypatch, fake_openai_key, temp_db, doc_db):
    from apps.core import router
    from apps.core import documents

    r1 = documents.ingest_text("relevant.txt", "src", "exact keyword appears here")
    documents.ingest_text("irrelevant.txt", "src", "totally different words")

    captured = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured.append(list(msgs))
        from tests.test_function_calling import _response_with, _message
        return _response_with(_message("got it"))

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    router.chat_with_rag(sid, "keyword", doc_ids=[r1["doc_id"]])
    user_msg = captured[0][-1]["content"]
    assert "exact keyword" in user_msg
    assert "totally different" not in user_msg


def test_chat_with_rag_tool_log_empty_for_pure_text(monkeypatch, fake_openai_key, temp_db):
    from apps.core import router

    monkeypatch.setattr(router, "_call_model", _make_chat_returning("ok"))
    sid = router.new_session()
    _, tool_log, _ = router.chat_with_rag(sid, "hi")
    assert tool_log == []
