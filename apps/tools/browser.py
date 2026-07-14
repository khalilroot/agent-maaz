from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

DDG_URL = "https://duckduckgo.com/html/?q={query}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 20.0

_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )
    return _client


def _resolve_ddg_redirect(href: str) -> str:
    if "uddg=" not in href:
        return href
    try:
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    except Exception:
        pass
    return href.replace("&amp;", "&")


def search(query: str, max_results: int = 5) -> list[dict]:
    response = get_client().get(
        DDG_URL.format(query=query),
        params={"q": query},
    )
    response.raise_for_status()
    html = response.text

    pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    tag_strip = re.compile(r"<[^>]+>")
    out: list[dict] = []
    seen: set[str] = set()
    for href, raw_title in pattern.findall(html):
        clean_href = _resolve_ddg_redirect(href)
        clean_title = tag_strip.sub("", raw_title).strip()
        if clean_href in seen or not clean_title:
            continue
        seen.add(clean_href)
        out.append({"title": clean_title, "url": clean_href})
        if len(out) >= max_results:
            break
    return out


def fetch(url: str, max_length: int = 5000) -> str:
    response = get_client().get(url)
    response.raise_for_status()
    html = response.text
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:max_length]


if __name__ == "__main__":
    print("--- browser.search ---")
    for r in search("agent-maaz open source AI"):
        print(f"  - {r['title'][:80]}")
        print(f"    {r['url'][:80]}")
    print()
    print("--- browser.fetch ---")
    page = fetch("https://duckduckgo.com")
    print(page[:300] + "...")
