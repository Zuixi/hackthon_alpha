"""Session search tool — search past conversation transcripts via FTS5.

Provides the agent with long-term recall across sessions.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agent.tools.registry import registry, tool_error

logger = logging.getLogger(__name__)

SESSION_SEARCH_SCHEMA = {
    "name": "session_search",
    "description": (
        "Search past conversation transcripts to recall previous interactions. "
        "Use when the user refers to past discussions, or to check if a topic "
        "was discussed before. Returns matching message snippets grouped by session.\n\n"
        "If query is empty, lists recent sessions instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query. Empty to list recent sessions.",
            },
            "role_filter": {
                "type": "string",
                "description": "Filter by role: 'user', 'assistant', or empty for all.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 20).",
                "default": 20,
            },
        },
        "required": [],
    },
}


def _format_timestamp(ts) -> str:
    if ts is None:
        return "unknown"
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        return str(ts)
    except (ValueError, OSError):
        return str(ts)


def register_session_search_tool(session_db) -> None:
    """Register session_search tool with the given SessionDB instance."""

    async def _handler(args: Dict[str, Any]) -> str:
        query = args.get("query", "").strip()
        role_filter_str = args.get("role_filter", "")
        limit = min(args.get("limit", 20), 50)

        role_filter = [role_filter_str] if role_filter_str else None

        if not query:
            sessions = session_db.list_sessions(limit=limit)
            if not sessions:
                return json.dumps({"message": "No past sessions found.", "sessions": []})
            result = []
            for s in sessions:
                result.append({
                    "session_id": s["id"],
                    "title": s.get("title") or "(untitled)",
                    "started": _format_timestamp(s.get("started_at")),
                    "messages": s.get("message_count", 0),
                })
            return json.dumps({"sessions": result}, ensure_ascii=False)

        raw_results = session_db.search_messages(
            query=query,
            role_filter=role_filter,
            limit=limit,
        )

        if not raw_results:
            return json.dumps({"message": f"No results for '{query}'.", "results": []})

        by_session: Dict[str, Dict[str, Any]] = {}
        for r in raw_results:
            sid = r["session_id"]
            if sid not in by_session:
                by_session[sid] = {
                    "session_id": sid,
                    "title": r.get("session_title") or "(untitled)",
                    "started": _format_timestamp(r.get("session_started")),
                    "matches": [],
                }
            by_session[sid]["matches"].append({
                "role": r["role"],
                "snippet": r.get("snippet") or (r.get("content", "")[:200]),
                "time": _format_timestamp(r.get("timestamp")),
            })

        sessions = list(by_session.values())[:10]
        return json.dumps({"query": query, "sessions": sessions}, ensure_ascii=False)

    registry.register(
        name="session_search",
        schema=SESSION_SEARCH_SCHEMA,
        handler=_handler,
        is_async=True,
    )
