from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_search_routes_to_router():
    from apps.core import router
    import json
    out = router.execute_tool("wikipedia_search", {"query": "Egypt", "lang": "en"})
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    assert "title" in parsed[0]
    assert "snippet" in parsed[0]
    assert "page_id" in parsed[0]


def test_summary_routes_to_router():
    from apps.core import router
    import json
    out = router.execute_tool(
        "wikipedia_summary",
        {"title": "Egypt", "lang": "en", "sentences": 3},
    )
    parsed = json.loads(out)
    assert parsed["title"] == "Egypt"
    assert parsed["extract"] is not None
    assert len(parsed["extract"]) > 50
    assert "url" in parsed


def test_search_supports_arabic(monkeypatch):
    from apps.core import router
    import json
    out = router.execute_tool(
        "wikipedia_search",
        {"query": "القاهرة", "lang": "ar", "limit": 3},
    )
    parsed = json.loads(out)
    assert isinstance(parsed, list)


def test_search_handles_zero_results():
    from apps.core import router
    import json
    out = router.execute_tool(
        "wikipedia_search",
        {"query": "xyzabcunlikelytotbefoundanywhere", "lang": "en", "limit": 5},
    )
    parsed = json.loads(out)
    assert parsed == []


def test_summary_not_found_returns_empty_extract():
    from apps.core import router
    import json
    out = router.execute_tool(
        "wikipedia_summary",
        {"title": "XyzQrsNoArticleShouldMatchThisTitle9", "lang": "en"},
    )
    parsed = json.loads(out)
    assert parsed["extract"] is None


@pytest.mark.asyncio
async def test_search_uses_respx():
    import respx
    from apps.tools import wikipedia as wp

    with respx.mock(base_url="https://en.wikipedia.org") as rmock:
        rmock.get("/w/api.php").mock(
            return_value=httpx.Response(
                200,
                json={
                    "query": {
                        "search": [
                            {
                                "title": "Cairo",
                                "snippet": "<span>capital of Egypt</span>",
                                "pageid": 12345,
                            }
                        ]
                    }
                },
            )
        )
        wp._client = None
        results = wp.search("Cairo", "en", limit=5)
        assert len(results) == 1
        assert results[0]["title"] == "Cairo"
        assert results[0]["snippet"] == "capital of Egypt"


def test_languages_dict_has_expected_keys():
    from apps.tools import wikipedia as wp
    for code in ("en", "ar", "fr", "de", "es", "it", "pt", "ru", "zh", "ja", "ko"):
        assert code in wp.LANGS
