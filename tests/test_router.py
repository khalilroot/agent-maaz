from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class FakeCompletions:
    def __init__(self, replies, fail_first_n=0):
        self.replies = list(replies)
        self.fail_first_n = fail_first_n
        self.calls = []

    def create(self, **kwargs):
        model = kwargs.get("model")
        self.calls.append({"model": model, "kwargs": kwargs})
        if self.fail_first_n > 0:
            self.fail_first_n -= 1
            raise RuntimeError(f"simulated failure for {model}")
        if self.replies:
            return _make_response(self.replies.pop(0))
        return _make_response("")


class FakeChat:
    def __init__(self, replies, fail_first_n=0):
        self.completions = FakeCompletions(replies, fail_first_n)


class FakeClient:
    def __init__(self, replies, fail_first_n=0):
        self.chat = FakeChat(replies, fail_first_n)


def _make_response(content):
    class Choice:
        class Message:
            pass

        message = Message()
        message.content = content

    class R:
        choices = [Choice()]
        usage = None

    return R()


class FakeStream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __iter__(self):
        for c in self.chunks:
            yield _make_chunk(c)


def _make_chunk(content):
    class C:
        class D:
            content = content

        delta = D()
        choices = [C()]

    return C()


@pytest.fixture
def fake_completions(monkeypatch, fake_openai_key):
    from apps.core import router
    monkeypatch.setattr(router, "_call_model", lambda client, model, msgs, stream: _make_response("test reply"))
    return router


def test_new_session_returns_unique_sids(fake_openai_key):
    from apps.core import router
    sid1 = router.new_session(system="sys1")
    sid2 = router.new_session()
    assert sid1 != sid2
    assert router.get_session(sid1)[0]["role"] == "system"


def test_chat_appends_messages_to_session(fake_completions, fake_openai_key):
    from apps.core import router
    sid = router.new_session()
    reply = router.chat(sid, "hi")
    assert reply == "test reply"
    session = router.get_session(sid)
    assert len(session) == 2
    assert session[0] == {"role": "user", "content": "hi"}
    assert session[1] == {"role": "assistant", "content": "test reply"}


def test_chat_saves_to_persistent_memory(fake_completions, fake_openai_key, temp_db):
    from apps.core import router
    from apps.core import memory
    sid = router.new_session()
    router.chat(sid, "remember me")
    rows = memory.get_messages(sid)
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "remember me"


def test_chat_uses_explicit_model_when_provided(monkeypatch, fake_openai_key):
    from apps.core import router
    captured = []

    def mock_call(client, model, msgs, stream):
        captured.append(model)
        return _make_response("ok")

    monkeypatch.setattr(router, "_call_model", mock_call)
    sid = router.new_session()
    router.chat(sid, "hi", model="custom/model:free")
    assert captured == ["custom/model:free"]


def test_chat_falls_back_on_failure(monkeypatch, fake_openai_key):
    from apps.core import router
    captured = []

    def mock_call(client, model, msgs, stream):
        captured.append(model)
        if model == "test/primary:free":
            raise RuntimeError("primary down")
        return _make_response(f"reply from {model}")

    monkeypatch.setattr(router, "_call_model", mock_call)
    sid = router.new_session()
    reply = router.chat(sid, "hi")
    assert "reply from" in reply
    assert captured[0] == "test/primary:free"
    assert captured[1] != "test/primary:free"


def test_chat_raises_when_all_models_fail(monkeypatch, fake_openai_key):
    from apps.core import router

    def mock_call(client, model, msgs, stream):
        raise RuntimeError(f"always fails for {model}")

    monkeypatch.setattr(router, "_call_model", mock_call)
    sid = router.new_session()
    with pytest.raises(RuntimeError, match="all fallback"):
        router.chat(sid, "hi")


def test_reset_session_removes_session(monkeypatch, fake_openai_key):
    from apps.core import router
    monkeypatch.setattr(router, "_call_model", lambda *args, **kwargs: _make_response("ok"))
    sid = router.new_session()
    assert sid in router.SESSIONS
    router.reset_session(sid)
    assert sid not in router.SESSIONS


def test_reset_session_unknown_sid_is_noop(monkeypatch, fake_openai_key):
    from apps.core import router
    router.reset_session("does-not-exist")


def test_chat_stream_yields_chunks(monkeypatch, fake_openai_key):
    from apps.core import router

    chunks_data = ["Hel", "lo ", "World"]

    class Choice:
        def __init__(self, content):
            self.delta = type("D", (), {"content": content})()

    class Chunk:
        def __init__(self, content):
            self.choices = [Choice(content)]

    def mock_call(client, model, msgs, stream):
        return [Chunk(c) for c in chunks_data]

    monkeypatch.setattr(router, "_call_model", mock_call)

    sid = router.new_session()
    pieces = list(router.chat_stream(sid, "hi"))
    assert "".join(pieces) == "Hello World"


def test_fallback_chain_has_at_least_three_entries(fake_openai_key):
    from apps.core import router
    assert len(router.FALLBACK_CHAIN) >= 3
    assert all(isinstance(m, str) and m.endswith(":free") for m in router.FALLBACK_CHAIN)
