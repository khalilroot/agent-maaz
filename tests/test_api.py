from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def mock_router_chat(monkeypatch):
    import importlib
    from apps.core import router
    importlib.reload(router)
    from apps.api import server
    importlib.reload(server)
    monkeypatch.setattr(
        server.router, "chat",
        lambda sid, message, model=None: "mocked reply",
    )
    monkeypatch.setattr(
        server.router, "chat_stream",
        lambda sid, message, model=None: iter(["mocked ", "stream"]),
    )
    return server


@pytest.fixture
def client(mock_router_chat):
    from fastapi.testclient import TestClient
    mock_router_chat.app.dependency_overrides = {}
    from apps.api.server import app
    return TestClient(app)


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_chat_returns_sid_and_reply(client):
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    data = r.json()
    assert "sid" in data
    assert data["reply"] == "mocked reply"
    assert len(data["sid"]) > 0


def test_chat_uses_provided_sid(client):
    r = client.post("/chat", json={"message": "hi", "sid": "abc-123"})
    assert r.status_code == 200
    assert r.json()["sid"] == "abc-123"


def test_chat_accepts_system_prompt(client):
    r = client.post("/chat", json={"message": "hi", "system": "be brief"})
    assert r.status_code == 200


def test_chat_validates_required_message(client):
    r = client.post("/chat", json={})
    assert r.status_code in (400, 422)


def test_chat_stream_returns_text_plain(client):
    r = client.post("/chat/stream", json={"message": "hi"})
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    assert "x-session-id" in {k.lower() for k in r.headers.keys()}


def test_sessions_endpoint_returns_list(client):
    r = client.get("/sessions")
    assert r.status_code == 200
    assert "sessions" in r.json()


def test_sessions_all_returns_db_sessions(client, temp_db):
    r = client.get("/sessions/all")
    assert r.status_code == 200
    assert "sessions" in r.json()
    assert isinstance(r.json()["sessions"], list)


def test_session_messages_endpoint(client, temp_db):
    from apps.core import memory
    memory.save_message("sid-1", "user", "hi")
    memory.save_message("sid-1", "assistant", "hello")
    r = client.get("/sessions/sid-1/messages")
    assert r.status_code == 200
    data = r.json()
    assert data["sid"] == "sid-1"
    assert len(data["messages"]) == 2


def test_session_messages_unknown_sid_returns_empty(client, temp_db):
    r = client.get("/sessions/no-such-sid/messages")
    assert r.status_code == 200
    assert r.json()["messages"] == []
