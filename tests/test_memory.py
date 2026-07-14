from __future__ import annotations

from apps.core import memory


def test_init_db_creates_table(temp_db):
    assert temp_db.exists()
    with memory.get_conn() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "messages"


def test_save_and_get_messages(temp_db):
    memory.save_message("s1", "user", "hello")
    memory.save_message("s1", "assistant", "hi there")
    rows = memory.get_messages("s1")
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[1]["role"] == "assistant"


def test_save_message_includes_timestamp(temp_db):
    memory.save_message("s1", "user", "x")
    rows = memory.get_messages("s1")
    assert rows[0]["created_at"] > 0


def test_list_sgroups_empty(temp_db):
    assert memory.list_sessions() == []


def test_list_sessions(temp_db):
    memory.save_message("s1", "user", "a")
    memory.save_message("s2", "user", "b")
    memory.save_message("s1", "assistant", "c")
    sessions = memory.list_sessions()
    assert len(sessions) == 2
    sids = {s["sid"] for s in sessions}
    assert sids == {"s1", "s2"}
    s1 = next(s for s in sessions if s["sid"] == "s1")
    assert s1["turns"] == 2


def test_search_messages(temp_db):
    memory.save_message("s1", "user", "find keyword here")
    memory.save_message("s1", "assistant", "no match")
    memory.save_message("s2", "user", "another keyword mention")
    results = memory.search_messages("keyword")
    assert len(results) == 2


def test_search_finds_query_regardless_of_text_case(temp_db):
    memory.save_message("s1", "user", "Hello World")
    results = memory.search_messages("hello")
    assert len(results) >= 1
    assert any("Hello" in r["content"] for r in results)


def test_get_messages_returns_in_order(temp_db):
    messages = ["first", "second", "third"]
    for m in messages:
        memory.save_message("s1", "user", m)
    rows = memory.get_messages("s1")
    assert [r["content"] for r in rows] == messages


def test_persistence_across_connections(temp_db):
    memory.save_message("s1", "user", "persistent")
    with memory.get_conn() as conn:
        rows = conn.execute(
            "SELECT content FROM messages WHERE sid='s1'"
        ).fetchall()
    assert rows[0]["content"] == "persistent"
