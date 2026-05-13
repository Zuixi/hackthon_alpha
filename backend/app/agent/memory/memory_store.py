"""Bounded curated memory with file persistence.

Ported from Hermes-Agent tools/memory_tool.py. Two stores:
  - MEMORY.md: agent's personal notes (environment, conventions, lessons)
  - USER.md: user profile (preferences, style, habits)

Both are injected into the system prompt. The snapshot auto-refreshes after
every write so subsequent turns in the same session see updated content.
"""

import json
import logging
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENTRY_DELIMITER = "\n§\n"

_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
]


def _scan_memory_content(content: str) -> Optional[str]:
    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: content matches threat pattern '{pid}'."
    return None


class MemoryStore:
    """Bounded curated memory with file persistence. One instance per user."""

    def __init__(self, data_dir: Path, memory_char_limit: int = 2200, user_char_limit: int = 1375):
        self.data_dir = data_dir
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}

    def load_from_disk(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_entries = self._read_file(self.data_dir / "MEMORY.md")
        self.user_entries = self._read_file(self.data_dir / "USER.md")
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }

    def _path_for(self, target: str) -> Path:
        return self.data_dir / ("USER.md" if target == "user" else "MEMORY.md")

    def _entries_for(self, target: str) -> List[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set_entries(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        return len(ENTRY_DELIMITER.join(entries)) if entries else 0

    def _char_limit(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    def save_to_disk(self, target: str):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._write_file(self._path_for(target), self._entries_for(target))
        self._refresh_snapshot(target)

    def _refresh_snapshot(self, target: str):
        """Rebuild the system prompt snapshot for the given target after a write."""
        entries = self._entries_for(target)
        self._system_prompt_snapshot[target] = self._render_block(target, entries)

    def add(self, target: str, content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}
        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        entries = self._entries_for(target)
        limit = self._char_limit(target)
        if content in entries:
            return self._success_response(target, "Entry already exists.")

        new_entries = entries + [content]
        new_total = len(ENTRY_DELIMITER.join(new_entries))
        if new_total > limit:
            current = self._char_count(target)
            return {
                "success": False,
                "error": f"Memory at {current}/{limit} chars. Adding ({len(content)} chars) would exceed limit.",
                "current_entries": entries,
            }
        entries.append(content)
        self._set_entries(target, entries)
        self.save_to_disk(target)
        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        old_text, new_content = old_text.strip(), new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove'."}
        scan_error = _scan_memory_content(new_content)
        if scan_error:
            return {"success": False, "error": scan_error}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1 and len({e for _, e in matches}) > 1:
            return {"success": False, "error": f"Multiple entries matched. Be more specific."}

        idx = matches[0][0]
        test_entries = entries.copy()
        test_entries[idx] = new_content
        if len(ENTRY_DELIMITER.join(test_entries)) > self._char_limit(target):
            return {"success": False, "error": "Replacement would exceed limit."}

        entries[idx] = new_content
        self._set_entries(target, entries)
        self.save_to_disk(target)
        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1 and len({e for _, e in matches}) > 1:
            return {"success": False, "error": "Multiple entries matched. Be more specific."}

        entries.pop(matches[0][0])
        self._set_entries(target, entries)
        self.save_to_disk(target)
        return self._success_response(target, "Entry removed.")

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """Return current snapshot for system prompt injection."""
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def _success_response(self, target: str, message: str = "") -> Dict[str, Any]:
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        resp: Dict[str, Any] = {
            "success": True,
            "target": target,
            "entries": entries,
            "usage": f"{pct}% — {current}/{limit} chars",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        return resp

    def _render_block(self, target: str, entries: List[str]) -> str:
        if not entries:
            return ""
        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        header = (
            f"USER PROFILE [{pct}% — {current}/{limit} chars]"
            if target == "user"
            else f"MEMORY [{pct}% — {current}/{limit} chars]"
        )
        sep = "═" * 46
        return f"{sep}\n{header}\n{sep}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []
        if not raw.strip():
            return []
        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    @staticmethod
    def _write_file(path: Path, entries: List[str]):
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".mem_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
