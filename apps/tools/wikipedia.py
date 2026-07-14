"""Wikipedia lookup via the free MediaWiki Action API. No API key required."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

USER_AGENT = "agent-maaz/0.1 (free open-source AI agent)"

LANGS = {
    "en": "en.wikipedia.org",
    "ar": "ar.wikipedia.org",
    "fr": "fr.wikipedia.org",
    "de": "de.wikipedia.org",
    "es": "es.wikipedia.org",
    "it": "it.wikipedia.org",
    "pt": "pt.wikipedia.org",
    "ru": "ru.wikipedia.org",
    "zh": "zh.wikipedia.org",
    "ja": "ja.wikipedia.org",
    "ko": "ko.wikipedia.org",
}

DEFAULT_TIMEOUT = 15.0

_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=DEFAULT_TIMEOUT,
        )
    return _client


def search(query: str, lang: str = "en", limit: int = 5) -> list[dict]:
    """Return list of matching article titles + short snippets."""
    host = LANGS.get(lang.lower(), "en.wikipedia.org")
    resp = get_client().get(
        f"https://{host}/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("query", {}).get("search", [])
    out: list[dict] = []
    for h in hits:
        snippet = re.sub(r"<[^>]+>", "", h.get("snippet", ""))
        out.append({
            "title": h.get("title", ""),
            "snippet": snippet,
            "page_id": h.get("pageid"),
        })
    return out


def summary(title: str, lang: str = "en", sentences: int = 5) -> dict:
    """Return the plain-text summary of a Wikipedia article."""
    host = LANGS.get(lang.lower(), "en.wikipedia.org")
    resp = get_client().get(
        f"https://{host}/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "exsentences": sentences,
            "titles": title,
            "format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return {"title": title, "extract": None}
    page = next(iter(pages.values()))
    extract = page.get("extract", "").strip()
    return {
        "title": page.get("title", title),
        "extract": extract or None,
        "url": f"https://{host}/wiki/{quote(title.replace(' ', '_'))}",
    }
