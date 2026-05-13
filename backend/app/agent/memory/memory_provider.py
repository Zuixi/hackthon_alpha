"""Abstract base class for pluggable memory providers.

Ported from Hermes-Agent agent/memory_provider.py with minimal changes.
Providers give the agent persistent recall across sessions.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier (e.g. 'builtin', 'honcho')."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if configured and ready. No network calls."""

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a session. Called once at agent startup."""

    def system_prompt_block(self) -> str:
        """Static text for the system prompt. Return empty to skip."""
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context before a turn. Return text or empty."""
        return ""

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """Persist a completed turn. Should be non-blocking."""

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return tool schemas in OpenAI function calling format."""

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def shutdown(self) -> None:
        """Clean shutdown."""

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Called when a session ends."""

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Extract insights before context compression. Return text or empty."""
        return ""
