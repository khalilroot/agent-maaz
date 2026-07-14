from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from apps.core import documents, memory, router  # noqa: E402
from apps.api import auth  # noqa: E402

WEB_DIR = Path(__file__).resolve().parents[2] / "apps" / "web"

app = FastAPI(title="agent-maaz")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/"):
        return await call_next(request)
    if not auth.check(request.headers.get("authorization")):
        return JSONResponse(
            status_code=401,
            content={"detail": auth.error_message()},
        )
    return await call_next(request)


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


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


class DocumentIngestRequest(BaseModel):
    name: str
    source: str = ""
    content: str


class RagChatRequest(BaseModel):
    sid: str | None = None
    message: str
    doc_ids: list[int] | None = None
    model: str | None = None
    system: str | None = None
    max_iterations: int = 5
    top_k: int = 3


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "auth_enabled": auth.is_enabled()}


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


@app.post("/chat/rag")
def chat_rag(req: RagChatRequest) -> dict:
    """RAG-augmented chat: searches local documents before LLM call."""
    sid = req.sid
    if not sid:
        sid = router.new_session(system=req.system)
    elif router.get_session(sid)[0].get("role") != "system" and req.system:
        router.get_session(sid).insert(0, {"role": "system", "content": req.system})
    reply, tool_log, rag_context = router.chat_with_rag(
        sid,
        req.message,
        doc_ids=req.doc_ids,
        model=req.model,
        max_iterations=req.max_iterations,
        top_k=req.top_k,
    )
    return {
        "sid": sid,
        "reply": reply,
        "tool_log": tool_log,
        "rag_context_chars": len(rag_context),
    }


@app.post("/documents/ingest")
def documents_ingest(req: DocumentIngestRequest) -> dict:
    """Ingest a document (text) — chunks it and stores in SQLite."""
    return documents.ingest_text(
        name=req.name, source=req.source or "api", text=req.content
    )


@app.post("/documents/ingest_file")
def documents_ingest_file(path: str) -> dict:
    """Ingest a file from disk by path. Server must have read access."""
    return documents.ingest_file(path)


@app.get("/documents")
def documents_list() -> dict:
    return {"documents": documents.list_documents(), "count": documents.get_doc_count()}


@app.delete("/documents/{doc_id}")
def documents_delete(doc_id: int) -> dict:
    deleted = documents.delete_document(doc_id)
    return {"deleted": deleted, "doc_id": doc_id}


@app.get("/documents/search")
def documents_search(q: str, limit: int = 5) -> dict:
    return {"query": q, "matches": documents.search_chunks(q, limit=limit)}


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
