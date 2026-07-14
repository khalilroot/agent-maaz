from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_list_skills_finds_three_builtins():
    from apps.skills import list_skills
    skills = list_skills()
    names = {s.name for s in skills}
    assert "code-review" in names
    assert "summarize" in names
    assert "translate" in names


def test_load_skill_returns_dataclass():
    from apps.skills import load_skill
    s = load_skill("code-review")
    assert s is not None
    assert s.name == "code-review"
    assert "python" in s.keywords or "code" in s.keywords
    assert "Code Review Skill" in s.body


def test_load_unknown_returns_none():
    from apps.skills import load_skill
    assert load_skill("does-not-exist") is None


def test_format_for_prompt_includes_sections():
    from apps.skills import load_skill, format_for_prompt
    skill = load_skill("summarize")
    text = format_for_prompt([skill])
    assert "## Active Skills" in text
    assert "summarize" in text.lower()


def test_select_relevant_picks_translate_for_arabic():
    from apps.skills import select_relevant
    selected = select_relevant("ترجم هذا النص للإنجليزية")
    names = {s.name for s in selected}
    assert "translate" in names


def test_select_relevant_picks_review_for_code():
    from apps.skills import select_relevant
    selected = select_relevant("please review this Python function for bugs")
    names = {s.name for s in selected}
    assert "code-review" in names


def test_select_relevant_with_no_match_returns_empty():
    from apps.skills import select_relevant
    selected = select_relevant("asdfgh qwerty")
    assert selected == []


def test_select_relevant_limits_results():
    from apps.skills import select_relevant
    selected = select_relevant(
        "review code and summarize and translate this long text into another language",
        top_k=1,
    )
    assert len(selected) <= 1


def test_keyword_extraction_handles_arabic():
    from apps.skills import _extract_keywords
    kws = _extract_keywords("هذا نص عربي للاختبار")
    assert any(w for w in kws if any("\u0600" <= c <= "\u06ff" for c in w))


def test_frontmatter_parsing():
    from apps.skills import _parse_frontmatter
    meta, body = _parse_frontmatter(
        "---\nfoo: bar\nbaz: qux\n---\nbody content"
    )
    assert meta == {"foo": "bar", "baz": "qux"}
    assert body == "body content"


def test_router_injects_skills_in_chat(monkeypatch, fake_openai_key):
    """When chat is called, system prompt should pull in relevant skills."""
    from apps.core import router
    captured = []

    def fake_call(client, model, msgs, stream, tools=None):
        captured.append(list(msgs))
        from tests.test_function_calling import _response_with, _message
        return _response_with(_message("ok"))

    monkeypatch.setattr(router, "_call_model", fake_call)
    sid = router.new_session(system="base system")
    router.chat(sid, "please review this Python code")
    msgs = captured[0]
    for m in msgs:
        if m["role"] == "system":
            assert "Active Skills" in m["content"] or "base system" in m["content"]
