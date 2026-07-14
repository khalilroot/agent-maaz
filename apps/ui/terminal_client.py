from __future__ import annotations

import sys
from pathlib import Path
from typing import AsyncIterator

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_SYSTEM = "انت مساعد ذكي اسمه agent-maaz. بترد بالعربي. خلي ردك قصير ومباشر."


class AgentMaazClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        system: str | None = DEFAULT_SYSTEM,
        timeout: float = 60.0,
    ):
        self.base_url = base_url
        self.system = system
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self.sid: str | None = None

    async def aclose(self) -> None:
        await self.client.aclose()

    async def health(self) -> dict:
        r = await self.client.get("/health")
        r.raise_for_status()
        return r.json()

    def _chat_payload(self, message: str) -> dict:
        payload: dict = {"message": message}
        if self.sid:
            payload["sid"] = self.sid
        elif self.system:
            payload["system"] = self.system
        return payload

    async def chat_stream(self, message: str) -> str:
        chunks: list[str] = []
        async for chunk in self.chat_stream_iter(message):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_stream_iter(self, message: str) -> AsyncIterator[str]:
        payload = self._chat_payload(message)
        async with self.client.stream("POST", "/chat/stream", json=payload) as resp:
            new_sid = resp.headers.get("x-session-id")
            if new_sid and not self.sid:
                self.sid = new_sid
            async for chunk in resp.aiter_text():
                if chunk:
                    yield chunk

    async def chat(self, message: str) -> str:
        r = await self.client.post("/chat", json=self._chat_payload(message))
        r.raise_for_status()
        data = r.json()
        if data.get("sid") and not self.sid:
            self.sid = data["sid"]
        return data["reply"]

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        r = await self.client.get("/search", params={"q": query, "max_results": max_results})
        r.raise_for_status()
        return r.json().get("results", [])

    async def chat_tools(self, message: str) -> dict:
        r = await self.client.post("/chat/tools", json=self._chat_payload(message))
        r.raise_for_status()
        data = r.json()
        if data.get("sid") and not self.sid:
            self.sid = data["sid"]
        return data
