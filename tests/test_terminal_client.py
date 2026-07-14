from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def streamed_text_chunks():
    return ["Mer", "h", "aba!", "\nأهلا", " بك"]


@pytest.mark.asyncio
async def test_chat_stream_iter_yields_each_chunk(streamed_text_chunks):
    from apps.ui.terminal_client import AgentMaazClient

    import respx

    with respx.mock() as rmock:
        rmock.post("http://localhost:8000/chat/stream").mock(
            return_value=httpx.Response(
                200,
                content=b"".join(c.encode("utf-8") for c in streamed_text_chunks),
            )
        )
        client = AgentMaazClient(base_url="http://localhost:8000")
        received = []
        async for chunk in client.chat_stream_iter("hello"):
            received.append(chunk)
        await client.aclose()

    assert "".join(received) == "".join(streamed_text_chunks)
    assert len(received) >= 1


@pytest.mark.asyncio
async def test_chat_stream_iter_sets_sid_from_header():
    from apps.ui.terminal_client import AgentMaazClient

    import respx

    with respx.mock() as rmock:
        rmock.post("http://localhost:8000/chat/stream").mock(
            return_value=httpx.Response(
                200,
                headers={"x-session-id": "fresh-sid-123"},
                content=b"hi",
            )
        )
        client = AgentMaazClient(base_url="http://localhost:8000")
        async for _ in client.chat_stream_iter("hi"):
            pass
        await client.aclose()
        assert client.sid == "fresh-sid-123"


@pytest.mark.asyncio
async def test_chat_stream_reuses_accumulated_iter():
    from apps.ui.terminal_client import AgentMaazClient

    import respx

    with respx.mock() as rmock:
        rmock.post("http://localhost:8000/chat/stream").mock(
            return_value=httpx.Response(
                200,
                content=b"Hel" b"lo " b"World",
            )
        )
        client = AgentMaazClient(base_url="http://localhost:8000")
        full = await client.chat_stream("hi")
        await client.aclose()
        assert full == "Hello World"


@pytest.mark.asyncio
async def test_chat_stream_iter_skips_empty_chunks():
    from apps.ui.terminal_client import AgentMaazClient

    import respx

    with respx.mock() as rmock:
        rmock.post("http://localhost:8000/chat/stream").mock(
            return_value=httpx.Response(
                200,
                content=b"a" + b"" + b"b" + b"" + b"c",
            )
        )
        client = AgentMaazClient(base_url="http://localhost:8000")
        chunks = [c async for c in client.chat_stream_iter("hi")]
        await client.aclose()
        assert "".join(chunks) == "abc"
