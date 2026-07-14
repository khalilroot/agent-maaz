from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def search_html():
    return """
    <html><body>
    <div class="result">
        <a class="result__a" href="https://example.com/1">First Result Title</a>
    </div>
    <div class="result">
        <a class="result__a" href="https://example.com/2">Second Result</a>
    </div>
    <div class="result">
        <a class="result__a" href="https://example.com/3">Third Thing</a>
    </div>
    </body></html>
    """


@pytest.fixture
def search_html_ddg_redirects():
    return """
    <html><body>
    <div class="result">
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Fkhalilroot%2Fagent%2Dmaaz">Real Link</a>
    </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_search_returns_results(monkeypatch, respx_mock, search_html):
    from apps.tools import browser

    respx_mock.get("https://duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text=search_html)
    )
    results = browser.search("test query", max_results=5)
    assert len(results) == 3
    assert results[0]["title"] == "First Result Title"
    assert results[0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_search_respects_max_results(monkeypatch, respx_mock, search_html):
    from apps.tools import browser

    respx_mock.get("https://duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text=search_html)
    )
    results = browser.search("test", max_results=2)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_deduplicates_urls(monkeypatch, respx_mock):
    from apps.tools import browser

    dup_html = """
    <html><body>
    <a class="result__a" href="https://x.com">Title A</a>
    <a class="result__a" href="https://x.com">Title A Again</a>
    <a class="result__a" href="https://x.com">Title A Repeat</a>
    </body></html>
    """
    respx_mock.get("https://duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text=dup_html)
    )
    results = browser.search("test", max_results=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_decodes_html_entities(monkeypatch, respx_mock, search_html_ddg_redirects):
    from apps.tools import browser

    respx_mock.get("https://duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text=search_html_ddg_redirects)
    )
    results = browser.search("agent", max_results=5)
    assert len(results) == 1
    assert "github.com/khalilroot/agent-maaz" in results[0]["url"]


@pytest.mark.asyncio
async def test_search_handles_empty_html(monkeypatch, respx_mock):
    from apps.tools import browser

    respx_mock.get("https://duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    results = browser.search("noresult", max_results=5)
    assert results == []


@pytest.mark.asyncio
async def test_fetch_strips_html_tags(monkeypatch, respx_mock):
    from apps.tools import browser

    html = """
    <html><body>
    <script>alert('x')</script>
    <style>body { color: red; }</style>
    <h1>Title</h1>
    <p>Hello world.</p>
    </body></html>
    """
    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(200, text=html)
    )
    text = browser.fetch("https://example.com")
    assert "alert" not in text
    assert "color: red" not in text
    assert "Title" in text
    assert "Hello world" in text


@pytest.mark.asyncio
async def test_fetch_respects_max_length(monkeypatch, respx_mock):
    from apps.tools import browser

    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(200, text="x" * 10000)
    )
    text = browser.fetch("https://example.com", max_length=100)
    assert len(text) == 100


@pytest.mark.asyncio
async def test_fetch_normalizes_whitespace(monkeypatch, respx_mock):
    from apps.tools import browser

    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(200, text="<p>a   b\n\n\nc</p>")
    )
    text = browser.fetch("https://example.com")
    assert "a b c" == text.strip()
