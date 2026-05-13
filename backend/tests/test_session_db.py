"""Tests for SessionDB (SQLite + FTS5)."""

import tempfile
from pathlib import Path

from app.agent.session.session_db import SessionDB


class TestSessionDB:
    def _make_db(self, tmp):
        return SessionDB(Path(tmp) / "test_sessions.db")

    def test_ensure_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_db(tmp)
            db.ensure_session("s1", user_id="u1")
            db.ensure_session("s1", user_id="u1")  # idempotent
            sessions = db.list_sessions()
            assert len(sessions) == 1
            assert sessions[0]["id"] == "s1"
            db.close()

    def test_append_and_get_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_db(tmp)
            db.ensure_session("s1", user_id="u1")
            db.append_message("s1", "user", "Hello")
            db.append_message("s1", "assistant", "Hi there")

            msgs = db.get_messages("s1")
            assert len(msgs) == 2
            assert msgs[0]["role"] == "user"
            assert msgs[0]["content"] == "Hello"
            assert msgs[1]["role"] == "assistant"
            db.close()

    def test_search_fts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_db(tmp)
            db.ensure_session("s1", user_id="u1")
            db.append_message("s1", "user", "Tell me about machine learning")
            db.append_message("s1", "assistant", "Machine learning is a branch of AI")

            db.ensure_session("s2", user_id="u1")
            db.append_message("s2", "user", "What is cooking?")

            results = db.search_messages("machine learning")
            assert len(results) >= 1
            found_sessions = [r["session_id"] for r in results]
            assert "s1" in found_sessions
            db.close()

    def test_empty_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_db(tmp)
            results = db.search_messages("nonexistent term xyz")
            assert results == []
            db.close()

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_db(tmp)
            db.ensure_session("s1", user_id="u1", title="Session 1")
            db.ensure_session("s2", user_id="u1", title="Session 2")

            sessions = db.list_sessions()
            assert len(sessions) == 2
            db.close()
