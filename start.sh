#!/usr/bin/env bash
# agent-maaz launcher — runs from any cwd.
#
#   ./start.sh install   create .venv + install deps + .env template
#   ./start.sh server    run FastAPI server (foreground, port 8000)
#   ./start.sh ui        run terminal TUI (needs server running elsewhere)
#   ./start.sh test      run pytest suite
#   ./start.sh stop      stop background server (when started with nohup)

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8000}"
PID_FILE="$SCRIPT_DIR/.agent-maaz.pid"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

cmd="${1:-server}"

ensure_venv() {
  if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "[*] creating .venv..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$PYTHON" -m pip install --upgrade pip >/dev/null
  fi
}

ensure_installed() {
  ensure_venv
  if ! "$PYTHON" -c "import fastapi, openai, dotenv" 2>/dev/null; then
    echo "[*] installing package + dev deps..."
    "$PYTHON" -m pip install -e ".[dev]" >/dev/null
    "$PYTHON" -m pip install eval-type-backport >/dev/null || true
  fi
}

case "$cmd" in
  install)
    ensure_installed
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
      cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
      echo "[ok] copied .env.example → .env (edit it to add OPENROUTER_API_KEY)"
    fi
    echo "[ok] ready. next: ./start.sh server"
    ;;
  server)
    ensure_installed
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
      echo "[err] .env missing. run: ./start.sh install"
      exit 1
    fi
    echo "[*] starting server on http://localhost:$PORT  (Ctrl+C to stop)"
    exec "$PYTHON" -m uvicorn apps.api.server:app --host 0.0.0.0 --port "$PORT"
    ;;
  ui)
    ensure_installed
    exec "$PYTHON" apps/ui/terminal.py
    ;;
  web)
    echo "[*] open http://localhost:$PORT/ in your browser"
    ;;
  test)
    ensure_installed
    exec "$PYTHON" -m pytest tests/
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      kill "$PID" 2>/dev/null && echo "[ok] stopped $PID" || echo "[!] failed to stop $PID"
      rm -f "$PID_FILE"
    else
      echo "[*] no pid file at $PID_FILE"
    fi
    ;;
  *)
    echo "usage: $0 {install|server|ui|web|test|stop}"
    exit 1
    ;;
esac
