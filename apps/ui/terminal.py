from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog

from apps.ui.terminal_client import AgentMaazClient


class AgentMaazTUI(App):
    CSS = """
    Screen { background: $surface; }
    #log { padding: 1 2; }
    #input { dock: bottom; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "quit"),
        ("ctrl+d", "quit", "quit"),
    ]

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.agent = AgentMaazClient(base_url=base_url)

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", wrap=True, markup=True)
        yield Input(id="input", placeholder="اكتب رسالتك هنا... (Ctrl+C للخروج)")

    async def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.write("[bold cyan]agent-maaz[/] connecting...")
        try:
            h = await self.agent.health()
            log.write(f"[bold cyan]agent-maaz[/] ready ({h.get('status', '?')})")
        except Exception as e:
            log.write(f"[red]connect failed: {e}[/]")
            log.write(f"[yellow]hint:[/] start server with: python3 -m apps.api.server")

    @on(Input.Submitted, "#input")
    async def on_submit(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if text.lower() in ("exit", "quit", "q"):
            self.exit()
            return
        log = self.query_one("#log", RichLog)
        log.write(f"[bold green]you>[/] {text}")
        try:
            if text.startswith("/search "):
                q = text[len("/search "):]
                log.write(f"[bold cyan]searching:[/] {q}")
                results = await self.agent.search(q)
                for r in results[:5]:
                    log.write(f"  [link={r['url']}][cyan]{r['title'][:80]}[/][/]")
                return
            if text.startswith("/agent "):
                prompt = text[len("/agent "):]
                log.write(f"[bold cyan]agent-maaz (with tools)>[/] ", end="")
                data = await self.agent.chat_tools(prompt)
                for entry in data.get("tool_log", []):
                    log.write(f"\n[dim]  ⚙ {entry['tool']}({list(entry['args'].keys())}) -> {entry['result_excerpt'][:80]}[/]")
                log.write(f"\n[bold cyan]answer>[/] {data['reply']}")
                return
            log.write("[bold cyan]agent-maaz>[/] ", end="")
            reply = await self.agent.chat_stream(text)
            log.write(reply)
            log.write("")
        except Exception as e:
            log.write(f"\n[red]error: {e}[/]")

    async def on_unmount(self) -> None:
        await self.agent.aclose()


if __name__ == "__main__":
    import os
    url = os.getenv("AGENT_MAAZ_BASE_URL", "http://localhost:8000")
    AgentMaazTUI(base_url=url).run()
