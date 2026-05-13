"""Memory tool — wraps MemoryStore as a MemoryProvider and agent tool.

The LLM uses this to proactively save user preferences, environment facts,
and lessons learned across sessions.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.agent.memory.memory_provider import MemoryProvider
from app.agent.memory.memory_store import MemoryStore
from app.agent.tools.registry import registry, tool_error

_SELF_REF_RE = re.compile(
    r"(?:我(?:叫|是|的名字|被称为|喜欢|偏好|习惯|倾向|不喜欢|讨厌|更喜欢))"
    r"|(?:请(?:记住|记下|注意|称呼我))"
    r"|(?:(?:以后|之后|下次).*(?:用|按|叫))",
    re.IGNORECASE,
)

MEMORY_SCHEMA = {
    "name": "memory",
    "description": (
        "Save durable information to persistent memory that survives across sessions. "
        "Memory is injected into future sessions, so keep it compact.\n\n"
        "WHEN TO SAVE (proactively):\n"
        "- User corrects you or says 'remember this'\n"
        "- User shares a preference or personal detail (name, style, interests)\n"
        "- You learn a convention or workflow specific to this user\n\n"
        "TWO TARGETS:\n"
        "- 'user': who the user is — name, preferences, communication style\n"
        "- 'memory': your notes — environment facts, conventions, lessons learned\n\n"
        "ACTIONS: add (new entry), replace (update existing), remove (delete).\n"
        "For replace/remove, use a short unique substring in old_text to identify the entry."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "The action to perform.",
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Which store: 'memory' for notes, 'user' for user profile.",
            },
            "content": {
                "type": "string",
                "description": "Entry content. Required for 'add' and 'replace'.",
            },
            "old_text": {
                "type": "string",
                "description": "Short unique substring to identify entry for replace/remove.",
            },
        },
        "required": ["action", "target"],
    },
}


class BuiltinMemoryProvider(MemoryProvider):
    """Built-in file-backed memory provider using MemoryStore."""

    def __init__(self, data_dir: Path, memory_char_limit: int = 2200, user_char_limit: int = 1375):
        self._store = MemoryStore(data_dir, memory_char_limit=memory_char_limit, user_char_limit=user_char_limit)

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def store(self) -> MemoryStore:
        return self._store

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._store.load_from_disk()

    def reload_for_user(self, data_dir: Path) -> None:
        """Rebuild MemoryStore pointing to a new user directory and reload."""
        self._store = MemoryStore(
            data_dir,
            memory_char_limit=self._store.memory_char_limit,
            user_char_limit=self._store.user_char_limit,
        )
        self._store.load_from_disk()

    def system_prompt_block(self) -> str:
        parts = []
        mem = self._store.format_for_system_prompt("memory")
        if mem:
            parts.append(mem)
        usr = self._store.format_for_system_prompt("user")
        if usr:
            parts.append(usr)
        return "\n\n".join(parts)

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Extract user self-references from messages about to be discarded."""
        findings: List[str] = []
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                )
            if not content:
                continue
            if _SELF_REF_RE.search(content):
                snippet = content[:300].strip()
                findings.append(snippet)
        if not findings:
            return ""
        return "用户在即将被压缩的消息中提到：\n" + "\n---\n".join(findings[:5])

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [MEMORY_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if tool_name != "memory":
            return tool_error(f"Unknown tool: {tool_name}")

        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content")
        old_text = args.get("old_text")

        if target not in {"memory", "user"}:
            return tool_error(f"Invalid target '{target}'.")

        if action == "add":
            if not content:
                return tool_error("Content required for 'add'.")
            result = self._store.add(target, content)
        elif action == "replace":
            if not old_text:
                return tool_error("old_text required for 'replace'.")
            if not content:
                return tool_error("content required for 'replace'.")
            result = self._store.replace(target, old_text, content)
        elif action == "remove":
            if not old_text:
                return tool_error("old_text required for 'remove'.")
            result = self._store.remove(target, old_text)
        else:
            return tool_error(f"Unknown action '{action}'.")

        return json.dumps(result, ensure_ascii=False)


def register_memory_tool(
    data_dir: Path, memory_char_limit: int = 2200, user_char_limit: int = 1375
) -> BuiltinMemoryProvider:
    """Create and register the memory tool. Returns the provider instance."""
    provider = BuiltinMemoryProvider(data_dir, memory_char_limit=memory_char_limit, user_char_limit=user_char_limit)

    async def _handler(args: Dict[str, Any]) -> str:
        return provider.handle_tool_call("memory", args)

    registry.register(
        name="memory",
        schema=MEMORY_SCHEMA,
        handler=_handler,
        is_async=True,
    )
    return provider
