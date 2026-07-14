from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def bootstrap_py39_backports():
    from eval_type_backport import eval_type_backport  # noqa: F401


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "agent-maaz-test.db"
    monkeypatch.setattr("apps.core.memory.DB_PATH", db_path)
    from apps.core import memory
    memory.init_db()
    return db_path


@pytest.fixture
def doc_db(tmp_path, monkeypatch):
    db = tmp_path / "docs-test.db"
    monkeypatch.setattr("apps.core.documents.DOC_DB_PATH", db)
    from apps.core import documents
    documents.init_db()
    return db


@pytest.fixture
def fake_openai_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test-fake-key-for-tests-only")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("AGENT_MAAZ_PRIMARY_MODEL", "test/primary:free")
