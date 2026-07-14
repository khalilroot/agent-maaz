from __future__ import annotations

import re
import urllib.parse
import urllib.request

DDG_URL = "https://duckduckgo.com/html/?q={query}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def search(query: str, max_results: int = 5) -> list[dict]:
    url = DDG_URL.format(query=urllib.parse.quote_plus(query))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    tag_strip = re.compile(r"<[^>]+>")
    out: list[dict] = []
    seen: set[str] = set()
    for href, raw_title in pattern.findall(html):
        clean_href = href.replace("&amp;", "&")
        clean_title = tag_strip.sub("", raw_title).strip()
        if clean_href in seen or not clean_title:
            continue
        seen.add(clean_href)
        out.append({"title": clean_title, "url": clean_href})
        if len(out) >= max_results:
            break
    return out


def fetch(url: str, max_length: int = 5000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")
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
