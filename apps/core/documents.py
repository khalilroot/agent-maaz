from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

DOC_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "documents.db"
DOC_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DOC_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                idx INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content ON chunks(content)")


_SENTENCE_SPLIT = re.compile(r"(?:\.\s|\?\s|!\s|\n\s*\n)")


def chunk_text(
    text: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            search_from = start + size // 2
            matches = list(re.finditer(_SENTENCE_SPLIT, text[search_from:end]))
            if matches:
                end = search_from + matches[-1].end()
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def ingest_text(name: str, source: str, text: str) -> dict:
    chunks = chunk_text(text)
    now = time.time()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO documents (name, source, created_at) VALUES (?, ?, ?)",
            (name, source, now),
        )
        doc_id = cur.lastrowid
        for idx, c in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (doc_id, idx, content, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, idx, c, now),
            )
    return {"doc_id": doc_id, "name": name, "chunks": len(chunks), "total_chars": len(text)}


def ingest_file(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(p)
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
    return ingest_text(name=p.name, source=str(p), text=text)


def _read_pdf(path: "Path") -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf not installed — run: pip install pypdf") from e
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n\n".join(parts)


def list_documents() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, source, created_at FROM documents ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_doc_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()
        return row["n"] if row else 0


def search_chunks(
    query: str,
    limit: int = 5,
    doc_ids: list[int] | None = None,
) -> list[dict]:
    tokens = [
        tok for tok in re.split(r"\W+", query.lower())
        if len(tok) >= 3
    ]
    if not tokens:
        return []

    where_parts: list[str] = []
    params: list = []
    for tok in tokens:
        where_parts.append("LOWER(c.content) LIKE ?")
        params.append(f"%{tok}%")
    sql = (
        "SELECT c.content, c.idx, d.name, d.id AS doc_id, d.source "
        "FROM chunks c JOIN documents d ON c.doc_id = d.id "
        f"WHERE {' OR '.join(where_parts)}"
    )
    if doc_ids:
        placeholders = ",".join("?" * len(doc_ids))
        sql += f" AND d.id IN ({placeholders})"
        params.extend(doc_ids)
    sql += " GROUP BY c.id ORDER BY c.id LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_document_chunks(doc_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT idx, content FROM chunks WHERE doc_id = ? ORDER BY idx",
            (doc_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        return cur.rowcount > 0


def format_rag_context(results: list[dict], max_chars: int = 4000) -> str:
    if not results:
        return ""
    parts: list[str] = []
    used = 0
    for r in results:
        prefix = f"[من: {r['name']}, chunk #{r['idx']}]\n"
        content = r["content"]
        leftover = max_chars - used - len(prefix)
        if leftover <= 0:
            break
        snippet = content[:leftover]
        parts.append(prefix + snippet)
        used += len(prefix) + len(snippet)
    return "\n\n---\n\n".join(parts)


init_db()
