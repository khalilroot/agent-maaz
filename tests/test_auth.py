from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_auth_disabled_by_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("AGENT_MAAZ_BEARER_TOKEN", raising=False)
    from apps.api import auth
    assert auth.is_enabled() is False
    assert auth.check(None) is True
    assert auth.check("Bearer anything") is True


def test_auth_enabled(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setenv("AGENT_MAAZ_BEARER_TOKEN", "secret-123")
    from apps.api import auth
    assert auth.is_enabled() is True
    assert auth.check(None) is False
    assert auth.check("") is False
    assert auth.check("Bearer wrong") is False
    assert auth.check("Bearer secret-123") is True
    assert auth.check("bearer secret-123") is True
    assert auth.check("Bearer  secret-123  ") is True


def test_auth_disabled_even_with_token_set(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENT_MAAZ_BEARER_TOKEN", "secret")
    from apps.api import auth
    assert auth.is_enabled() is False
    assert auth.check("Bearer wrong") is True


def test_auth_truthy_values(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "1")
    from apps.api import auth
    assert auth.is_enabled() is True
    monkeypatch.setenv("REQUIRE_AUTH", "yes")
    assert auth.is_enabled() is True
    monkeypatch.setenv("REQUIRE_AUTH", "on")
    assert auth.is_enabled() is True


def test_auth_disabled_without_token(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.delenv("AGENT_MAAZ_BEARER_TOKEN", raising=False)
    from apps.api import auth
    assert auth.check(None) is True
    assert auth.check("Bearer anything") is True


def test_fingerprint_is_stable():
    from apps.api import auth
    a = auth.fingerprint("abc")
    b = auth.fingerprint("abc")
    c = auth.fingerprint("def")
    assert a == b
    assert a != c
    assert len(a) == 16


def test_auth_health_endpoint_open(test_client_factory):
    from fastapi.testclient import TestClient
    client = TestClient(test_client_factory(require_auth=True, token="secret"))
    r = client.get("/health")
    assert r.status_code == 200


def test_auth_protected_endpoint_requires_token(test_client_factory):
    from fastapi.testclient import TestClient
    client = TestClient(test_client_factory(require_auth=True, token="secret"))
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_auth_protected_endpoint_accepts_valid_token(test_client_factory):
    from fastapi.testclient import TestClient
    client = TestClient(test_client_factory(require_auth=True, token="secret"))
    r = client.post(
        "/chat",
        headers={"Authorization": "Bearer secret"},
        json={"message": "hi"},
    )
    assert r.status_code == 200


def test_auth_disabled_globally(test_client_factory):
    from fastapi.testclient import TestClient
    client = TestClient(test_client_factory(require_auth=False))
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 200
