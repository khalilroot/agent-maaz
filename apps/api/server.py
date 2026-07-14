from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from apps.core import memory, router  # noqa: E402

app = FastAPI(title="agent-maaz")


class ChatRequest(BaseModel):
    sid: str | None = None
    message: str
    model: str | None = None
    system: str | None = None


class ToolsChatRequest(BaseModel):
    sid: str | None = None
    message: str
    model: str | None = None
    system: str | None = None
    max_iterations: int = 5


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    sid = req.sid or router.new_session(system=req.system)
    reply = router.chat(sid, req.message, model=req.model)
    return {"sid": sid, "reply": reply}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    sid = req.sid or router.new_session(system=req.system)

    def gen():
        for chunk in router.chat_stream(sid, req.message, model=req.model):
            yield chunk

    response = StreamingResponse(gen(), media_type="text/plain")
    response.headers["X-Session-Id"] = sid
    return response


@app.post("/chat/tools")
def chat_tools(req: ToolsChatRequest) -> dict:
    """LLM-driven tool use. Returns final answer + log of tool calls made."""
    sid = req.sid
    if not sid:
        sid = router.new_session(system=req.system)
    elif router.get_session(sid)[0].get("role") != "system" and req.system:
        router.get_session(sid).insert(0, {"role": "system", "content": req.system})
    reply, tool_log = router.chat_with_tools(
        sid, req.message, model=req.model, max_iterations=req.max_iterations
    )
    return {"sid": sid, "reply": reply, "tool_log": tool_log}


@app.get("/tools")
def list_tools() -> dict:
    """List tools registered for LLM-driven use."""
    return {"tools": router.TOOLS}


@app.get("/sessions")
def sessions_in_memory() -> dict:
    return {"sessions": list(router.SESSIONS.keys())}


@app.get("/sessions/all")
def sessions_all() -> dict:
    return {"sessions": memory.list_sessions()}


@app.get("/sessions/{sid}/messages")
def session_messages(sid: str) -> dict:
    return {"sid": sid, "messages": memory.get_messages(sid)}


@app.get("/search")
def search(q: str, max_results: int = 5) -> dict:
    from apps.tools import browser
    return {"query": q, "results": browser.search(q, max_results=max_results)}
