# Contributing to agent-maaz

Thanks for your interest. This project is intentionally small and personal —
the scope is "an agent I (and the people I share it with) actually use," not
"an agent competing with Manus or Devin." Practical fixes and personal-use
features are most welcome; big architectural rewrites are not.

## Quick start

```bash
git clone https://github.com/khalilroot/agent-maaz.git
cd agent-maaz
./start.sh install     # creates .venv + installs deps
# edit .env and add OPENROUTER_API_KEY
./start.sh test        # 101 tests should pass
./start.sh server      # http://localhost:8000
```

## Tests are required

Every commit that changes behavior should keep the test suite green:

```bash
./start.sh test
```

Add new tests in `tests/test_<module>.py` for any new module in `apps/`. We
mock all external dependencies (OpenRouter, DDG) so tests stay offline and
free. See existing files for the pattern (`respx` for HTTP, `monkeypatch` for
Python).

## File layout

- `apps/core/`    — orchestration primitives (router, memory, documents, auth)
- `apps/api/`     — FastAPI server, auth, rate limit
- `apps/ui/`      — terminal TUI + a reusable async HTTP client
- `apps/web/`     — single-page browser UI (vanilla JS, no build step)
- `apps/tools/`   — agent-callable tools (browser search + fetch)
- `tests/`        — pytest suite (101 tests as of v0.1)
- `Dockerfile`, `docker-compose.yml` — one-shot deploy
- `start.sh`      — local launcher

## Commit message style

This repo uses conventional-commit-ish prefixes:

- `feat(...)`  — new capability (e.g. `feat(rag): document upload`)
- `fix(...)`   — bug fix
- `chore(...)` — repo hygiene (config, ci, deps)
- `docs(...)`  — README / comments / docs
- `test(...)`  — test-only changes
- `refactor(...)` — internal cleanup without behavior change

## Reporting issues

There's no issue template yet. When filing, please include:

- the exact command you ran
- the exact output (errors, stack traces)
- your Python version (`python3 --version`)
- whether you started the server with `./start.sh server` vs Docker

## License

By contributing, you agree your contributions are MIT-licensed, same as the
rest of the project.
