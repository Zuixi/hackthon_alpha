"""SQLite-backed session storage with FTS5 search.

Simplified from Hermes hermes_state.py. Stores conversation transcripts
and provides full-text search across past sessions, with trigram tokenizer
for CJK text support.
"""

import json
import logging
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    model TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    message_count INTEGER DEFAULT 0,
    title TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""

FTS_TRIGRAM_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
    content,
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""


def _has_cjk(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text))


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user query for FTS5 MATCH syntax."""
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', ' ', query)
    tokens = cleaned.split()
    if not tokens:
        return '""'
    if len(tokens) == 1:
        return f'"{tokens[0]}"'
    return " ".join(f'"{t}"' for t in tokens)


class SessionDB:
    """SQLite session database with FTS5 full-text search."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._init_schema()
        return self._conn

    def _init_schema(self):
        conn = self._conn
        conn.executescript(SCHEMA_SQL)
        try:
            conn.executescript(FTS_SQL)
        except sqlite3.OperationalError as e:
            logger.warning("FTS5 init error (may already exist): %s", e)
        try:
            conn.executescript(FTS_TRIGRAM_SQL)
            self._has_trigram = True
        except sqlite3.OperationalError:
            self._has_trigram = False
            logger.info("Trigram FTS5 not available; CJK search will use LIKE fallback")
        conn.commit()

    def create_session(
        self, user_id: str = "", model: str = "", title: str = ""
    ) -> str:
        session_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions (id, user_id, model, started_at, title) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, model, time.time(), title),
        )
        conn.commit()
        return session_id

    def ensure_session(self, session_id: str, user_id: str = "", model: str = "", title: str = "") -> None:
        """Create session if it doesn't already exist (idempotent)."""
        conn = self._get_conn()
        existing = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO sessions (id, user_id, model, started_at, title) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, model, time.time(), title),
            )
            conn.commit()

    def end_session(self, session_id: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (time.time(), session_id),
        )
        conn.commit()

    def update_title(self, session_id: str, title: str) -> None:
        conn = self._get_conn()
        conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        conn.commit()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str = "",
        tool_name: str = "",
        tool_calls: Any = None,
        tool_call_id: str = "",
    ) -> int:
        conn = self._get_conn()
        tc_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
        cursor = conn.execute(
            """INSERT INTO messages (session_id, role, content, tool_call_id, tool_calls, tool_name, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, role, content, tool_call_id or None, tc_json, tool_name or None, time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            (session_id,),
        )
        conn.commit()
        return cursor.lastrowid

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_messages(
        self,
        query: str,
        role_filter: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search messages using FTS5 with CJK trigram fallback."""
        conn = self._get_conn()
        use_trigram = _has_cjk(query) and self._has_trigram

        if use_trigram:
            sanitized = _sanitize_fts5_query(query)
            sql = """
                SELECT m.*, s.title as session_title, s.started_at as session_started,
                       snippet(messages_fts_trigram, 0, '>>>', '<<<', '...', 64) as snippet
                FROM messages_fts_trigram fts
                JOIN messages m ON m.id = fts.rowid
                JOIN sessions s ON s.id = m.session_id
                WHERE messages_fts_trigram MATCH ?
            """
            params: list = [sanitized]
        elif _has_cjk(query):
            sql = """
                SELECT m.*, s.title as session_title, s.started_at as session_started,
                       substr(m.content, 1, 200) as snippet
                FROM messages m
                JOIN sessions s ON s.id = m.session_id
                WHERE m.content LIKE ?
            """
            params = [f"%{query}%"]
        else:
            sanitized = _sanitize_fts5_query(query)
            sql = """
                SELECT m.*, s.title as session_title, s.started_at as session_started,
                       snippet(messages_fts, 0, '>>>', '<<<', '...', 64) as snippet
                FROM messages_fts fts
                JOIN messages m ON m.id = fts.rowid
                JOIN sessions s ON s.id = m.session_id
                WHERE messages_fts MATCH ?
            """
            params = [sanitized]

        if role_filter:
            placeholders = ",".join("?" * len(role_filter))
            sql += f" AND m.role IN ({placeholders})"
            params.extend(role_filter)

        sql += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as e:
            logger.error("FTS5 search error: %s", e)
            return []

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
