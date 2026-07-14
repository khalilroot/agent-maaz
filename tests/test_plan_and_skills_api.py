from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _make_fake_router_call(sequence):
    """Return a fake _call_model that yields the given assistant content in order."""
    from tests.test_function_calling import _response_with, _message

    state = {"idx": 0, "calls": []}

    def fake_call(client, model, msgs, stream, tools=None):
        state["calls"].append((msgs, tools))
        i = state["idx"]
        content = sequence[i] if i < len(sequence) else "done"
        state["idx"] += 1
        return _response_with(_message(content))

    state["_call"] = fake_call
    state["reset"] = lambda: state.update({"idx": 0, "calls": []})
    return state


def test_plan_steps_parse_decimal_numbering():
    from apps.core.router import _parse_plan
    plan = "1. First step\n2. Second step\n3. Third step"
    steps = _parse_plan(plan, max_steps=10)
    assert steps == ["First step", "Second step", "Third step"]


def test_plan_steps_parse_arabic_numbering():
    from apps.core.router import _parse_plan
    plan = "١- ترجم النص\n٢- راجع النتيجة\n٣- حسّن الصياغة"
    steps = _parse_plan(plan, max_steps=10)
    assert len(steps) == 3
    assert "ترجم" in steps[0]


def test_plan_steps_parse_step_prefix():
    from apps.core.router import _parse_plan
    plan = "Step 1: collect data\nStep 2: analyze"
    steps = _parse_plan(plan, max_steps=10)
    assert len(steps) == 2
    assert steps[0] == "collect data"


def test_plan_steps_max_steps_caps():
    from apps.core.router import _parse_plan
    plan = "1. a\n2. b\n3. c\n4. d\n5. e"
    steps = _parse_plan(plan, max_steps=3)
    assert len(steps) == 3


def test_plan_steps_ignores_non_numbered():
    from apps.core.router import _parse_plan
    plan = "intro paragraph\n1. First\nrandom line\n2. Second"
    steps = _parse_plan(plan, max_steps=10)
    assert steps == ["First", "Second"]


def test_chat_with_plan_orchestrates_steps(monkeypatch, fake_openai_key):
    from apps.core import router

    state = _make_fake_router_call([
        "1. Plan step alpha\n2. Plan step beta",
        "result of alpha",
        "result of beta",
        "final answer here",
    ])
    monkeypatch.setattr(router, "_call_model", state["_call"])

    sid = router.new_session()
    plan, final, steps = router.chat_with_plan(sid, "do something complex")
    assert "alpha" in plan
    assert "beta" in plan
    assert len(steps) == 2
    assert "final answer here" in final


def test_chat_with_plan_falls_back_on_no_steps(monkeypatch, fake_openai_key):
    from apps.core import router

    state = _make_fake_router_call([
        "(no numbered steps)",
        "single pass reply",
    ])
    monkeypatch.setattr(router, "_call_model", state["_call"])

    sid = router.new_session()
    plan, final, steps = router.chat_with_plan(sid, "simple ask")
    assert "no numbered steps" in plan
    assert len(steps) == 1
    assert steps[0]["step"] == 0


def test_skills_endpoint_returns_three():
    """Default app should expose Skills via /skills via fresh test client."""
    import importlib
    from fastapi.testclient import TestClient
    from apps import skills as skills_mod
    importlib.reload(skills_mod)
    if "apps.api.server" in importlib.sys.modules:
        importlib.reload(importlib.sys.modules["apps.api.server"])
    from apps.api import server  # noqa: E402
    client = TestClient(server.app)
    r = client.get("/skills")
    assert r.status_code == 200
    data = r.json()
    names = {s["name"] for s in data["skills"]}
    assert {"code-review", "summarize", "translate"} <= names
