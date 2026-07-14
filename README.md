# agent-maaz

**Free open-source AI agent · $0 recurring cost · multi-layer fallback · web + terminal UI**

> Personal AI agent for people who can't afford subscriptions.
> Independent — no corporate control. MIT licensed.

---

## What it does

A working personal AI agent you can run on your own machine for **$0/month**:

- **Chat** in Arabic or English with persistent conversation memory
- **Multi-turn streaming** with full history (in-memory + SQLite)
- **Document RAG** — upload `.txt` / `.md` files, ask questions about them
- **Browser tool** — LLM can search the web (DuckDuckGo, no API key)
- **LLM function calling** — agent decides when to search autonomously
- **Web UI** (Claude-like) + **Terminal UI** (Textual TUI)
- **MIT licensed**, open-source, no telemetry, no vendor lock-in

---

## Quick start

### 1. Install

Requires **Python 3.9+**. We recommend using a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

For Python 3.9 you also need a typing-syntax bridge:
```bash
pip install eval-type-backport
```

### 2. Configure

```bash
cp .env.example .env
# then edit .env and add your OpenRouter API key (free tier works)
```

Get a free OpenRouter key at https://openrouter.ai/keys (free tier = 50 req/day).

### 3. Run

```bash
python3 -m uvicorn apps.api.server:app --port 8000
```

Open http://localhost:8000/ in your browser, or in another terminal:

```bash
python3 apps/ui/terminal.py
```

---

## Use with Docker

```bash
docker compose up --build
```

The compose file declares the env vars it needs (set them in `.env` first).
Data (conversations + document index) is persisted in `./data/`.

---

## Stack

| Layer | Choice | Cost |
|---|---|---|
| LLM | OpenRouter free tier · fallback chain across 5 verified free models | $0 |
| Embeddings | (none — uses LIKE-based search; vector upgrade planned) | $0 |
| Vector store | (none yet — SQLite + LIKE match for v1) | $0 |
| Database | SQLite (stdlib) — conversations + documents | $0 |
| Web framework | FastAPI | $0 |
| Terminal UI | Textual | $0 |
| Web UI | vanilla HTML/CSS/JS (no build step) | $0 |
| Browser tool | httpx + DDG HTML (no API key) | $0 |
| Persistence | SQLite + filesystem | $0 |
| **Total recurring** | **$0** | $0 |

---

## Architecture

```
                ┌──────────────────────────────┐
                │  User (Web UI / TUI / curl)   │
                └──────────────┬───────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼─────┐         ┌──────▼──────┐         ┌────▼────────┐
   │  /chat   │         │ /chat/tools │         │ /chat/rag   │
   │          │         │   (LLM-     │         │  (documents │
   │ streaming│         │   driven     │         │   context   │
   │  +sess.  │         │   tool use)  │         │   injected) │
   └────┬─────┘         └──────┬──────┘         └────┬────────┘
        └──────────────────────┴──────────────────────┘
                               │
                ┌──────────────▼───────────────┐
                │    apps/core/router.py          │
                │  OpenRouter + 5-model fallback │
                │  (auto-switches on failure)     │
                └──────────────┬───────────────┘
                               │
                ┌──────────────▼───────────────┐
                │   apps/core/{memory,documents} │
                │   SQLite persistence layer     │
                └──────────────┬───────────────┘
                               │
                ┌──────────────▼───────────────┐
                │      apps/tools/browser.py     │
                │   DuckDuckGo search + fetch     │
                └──────────────────────────────────┘
```

---

## Endpoints (HTTP API)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe (always open, no auth) |
| GET | `/` | Single-page Web UI (Claude-like) |
| POST | `/chat` | One-shot chat, returns `{sid, reply}` |
| POST | `/chat/stream` | Streaming chat (text/plain, `X-Session-Id` header) |
| POST | `/chat/tools` | Chat with LLM-driven tool use, returns `{reply, tool_log}` |
| POST | `/chat/rag` | RAG-augmented chat with doc context |
| GET | `/sessions` | Active in-memory sessions |
| GET | `/sessions/all` | DB-backed session list |
| GET | `/sessions/{sid}/messages` | Conversation history |
| GET | `/search?q=` | Web search via DDG |
| POST | `/documents/ingest` | Ingest text content |
| POST | `/documents/ingest_file` | Ingest a file from disk (server path) |
| GET | `/documents` | List ingested docs |
| DELETE | `/documents/{id}` | Remove doc |
| GET | `/documents/search?q=` | Search document chunks |
| GET | `/tools` | List LLM-callable tools |

All endpoints (except `/health` and `/`) require `Authorization: Bearer <token>`
if `REQUIRE_AUTH=true` is set in `.env`.

---

## Configuration (.env)

```ini
# OpenRouter (https://openrouter.ai/)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Model selection (free tier primary, falls back through 5 free models)
AGENT_MAAZ_PRIMARY_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free

# Auth (optional)
REQUIRE_AUTH=false
AGENT_MAAZ_BEARER_TOKEN=

# Rate limiting (per IP / per bearer token)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### Verified free models (fallback chain)

In rough order of capability:

1. `nvidia/nemotron-3-ultra-550b-a55b:free` (550B params, 1M ctx)
2. `meta-llama/llama-3.3-70b-instruct:free` (proven general-purpose)
3. `qwen/qwen3-coder:free` (1M ctx, code-specialized)
4. `nousresearch/hermes-3-llama-3.1-405b:free` (405B params)
5. `google/gemma-4-31b-it:free` (31B, multimodal)

OpenRouter updates this list periodically. Run `curl https://openrouter.ai/api/v1/models` for the current state.

---

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/        # 100+ tests
```

Tests run entirely offline (OpenRouter + DDG are mocked via `respx`).

CI runs on GitHub Actions across Python 3.9 / 3.10 / 3.11 / 3.12.

---

## Limits & caveats (v1 honestly)

- **Document RAG** uses keyword matching (LIKE), not vector embeddings. Semantic match quality is limited.
- **Search** uses DDG HTML interface — may rate-limit heavy use.
- **OpenRouter free tier** = 50 requests/day across all free models on your account.
- **Streaming output** is OpenRouter's `text/plain` chunks, not Server-Sent Events.
- **No multi-tenant auth** — single bearer token, intended for personal/small-group use.
- **Document ingest** supports plain text. PDF / DOCX / vision not yet supported.

---

## License

MIT — see [LICENSE](./LICENSE).
