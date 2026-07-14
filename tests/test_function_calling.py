from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _tool_call(name: str, args: dict, call_id: str = "tc_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(args),
        ),
    )


def _message(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content)
    msg.tool_calls = tool_calls or []
    return msg


def _choice(msg):
    return SimpleNamespace(message=msg)


def _response_with(msg):
    return SimpleNamespace(choices=[_choice(msg)], usage=None)


def _patch_tool(monkeypatch, name: str, return_value):
    from apps.tools import browser
    monkeypatch.setattr(browser, name, return_value)


def test_chat_with_tools_simple_no_tool_use(monkeypatch, fake_openai_key):
    from apps.core import router
    captured = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured.append({"model": model, "tools_passed": bool(tools)})
        return _response_with(_message("just a text answer"))

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "hi")
    assert reply == "just a text answer"
    assert log == []
    assert captured[0]["tools_passed"] is True
    assert any(m["role"] == "user" for m in router.get_session(sid))


def test_chat_with_tools_uses_browser_search_then_returns_text(monkeypatch, fake_openai_key):
    from apps.core import router

    fake_results = [{"title": "foo", "url": "https://x.com"}]

    def mock_search(query, max_results=5):
        return fake_results

    _patch_tool(monkeypatch, "search", mock_search)

    iter_states = iter(
        [
            _response_with(
                _message(
                    content=None,
                    tool_calls=[_tool_call("browser_search", {"query": "python decorators"})],
                )
            ),
            _response_with(_message("found Python docs at python.org")),
        ]
    )

    def fake_call(client, model, msgs, stream, tools=None):
        return next(iter_states)

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "Find Python docs")
    assert reply == "found Python docs at python.org"
    assert len(log) == 1
    assert log[0]["tool"] == "browser_search"
    assert log[0]["args"] == {"query": "python decorators"}


def test_chat_with_tools_uses_browser_fetch(monkeypatch, fake_openai_key):
    from apps.core import router

    def mock_fetch(url, max_length=5000):
        return "fetched content snippet"

    _patch_tool(monkeypatch, "fetch", mock_fetch)

    iter_states = iter(
        [
            _response_with(
                _message(
                    tool_calls=[_tool_call("browser_fetch", {"url": "https://python.org"})]
                )
            ),
            _response_with(_message("here's what the page says")),
        ]
    )

    monkeypatch.setattr(
        router,
        "_call_model",
        lambda *args, **kwargs: next(iter_states),
    )

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "read https://python.org")
    assert "here's what the page says" == reply
    assert len(log) == 1
    assert log[0]["tool"] == "browser_fetch"


def test_chat_with_tools_persists_full_conversation(monkeypatch, fake_openai_key, temp_db):
    from apps.core import router
    from apps.core import memory

    def mock_search(query, max_results=5):
        return [{"title": "x", "url": "y"}]

    _patch_tool(monkeypatch, "search", mock_search)

    iter_states = iter(
        [
            _response_with(
                _message(
                    tool_calls=[
                        _tool_call("browser_search", {"query": "x"})
                    ]
                )
            ),
            _response_with(_message("final answer")),
        ]
    )
    monkeypatch.setattr(
        router,
        "_call_model",
        lambda *args, **kwargs: next(iter_states),
    )

    sid = router.new_session()
    router.chat_with_tools(sid, "ask me")
    rows = memory.get_messages(sid)
    roles = [r["role"] for r in rows]
    assert "user" in roles
    assert "assistant" in roles


def test_chat_with_tools_handles_unknown_tool(monkeypatch, fake_openai_key):
    from apps.core import router
    tc = _tool_call("made_up_tool", {})
    iter_states = iter(
        [
            _response_with(_message(tool_calls=[tc])),
            _response_with(_message("ok")),
        ]
    )
    monkeypatch.setattr(
        router,
        "_call_model",
        lambda *args, **kwargs: next(iter_states),
    )

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "hi")
    assert "ok" == reply
    assert len(log) == 1
    assert log[0]["tool"] == "made_up_tool"
    assert "unknown tool" in log[0]["result_excerpt"]


def test_chat_with_tools_respects_iteration_cap(monkeypatch, fake_openai_key):
    from apps.core import router
    tc = _tool_call("browser_search", {"query": "x"})

    def always_tool_call(*args, **kwargs):
        return _response_with(_message(tool_calls=[tc]))

    monkeypatch.setattr(router, "_call_model", always_tool_call)

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "loop", max_iterations=3)
    assert "iteration cap" in reply or "cap" in reply.lower()
    assert len(log) == 3


def test_chat_with_tools_uses_explicit_model(monkeypatch, fake_openai_key):
    from apps.core import router
    captured = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured.append(model)
        return _response_with(_message("ok"))

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    router.chat_with_tools(sid, "hi", model="specific/model:free")
    assert captured[0] == "specific/model:free"


def test_chat_with_tools_falls_back_on_failure(monkeypatch, fake_openai_key):
    from apps.core import router
    captured = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured.append(model)
        if model == "test/primary:free":
            raise RuntimeError("primary down")
        return _response_with(_message(f"reply via {model}"))

    monkeypatch.setattr(router, "_call_model", fake_call)

    sid = router.new_session()
    reply, log = router.chat_with_tools(sid, "hi")
    assert captured[0] == "test/primary:free"
    assert "reply via" in reply
