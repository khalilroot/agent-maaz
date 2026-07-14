from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def bootstrap():
    from eval_type_backport import eval_type_backport  # noqa: F401


@pytest.fixture
def web_client():
    from fastapi.testclient import TestClient
    from apps.api.server import app
    return TestClient(app)


def test_index_serves_html(web_client):
    r = web_client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "<!DOCTYPE html>" in html
    assert "agent-maaz" in html
    assert "اكتب رسالتك" in html
    assert 'href="/static/style.css"' in html


def test_index_references_app_js(web_client):
    html = web_client.get("/").text
    assert 'src="/static/app.js"' in html


def test_static_style_css_served(web_client):
    r = web_client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers.get("content-type", "")


def test_static_app_js_served(web_client):
    r = web_client.get("/static/app.js")
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "") or r.headers.get("content-type", "").startswith("text/")


def test_static_unknown_404(web_client):
    r = web_client.get("/static/does-not-exist.js")
    assert r.status_code == 404
