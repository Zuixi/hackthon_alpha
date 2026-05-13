"""MemoryManager — orchestrates built-in and external memory providers.

Simplified from Hermes agent/memory_manager.py. Manages provider lifecycle,
builds system prompt blocks, and routes memory tool calls.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.agent.memory.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


class MemoryManager:
    """Orchestrates memory providers for the agent."""

    def __init__(self):
        self._providers: List[MemoryProvider] = []
        self._tool_to_provider: Dict[str, MemoryProvider] = {}

    def add_provider(self, provider: MemoryProvider) -> None:
        self._providers.append(provider)
        for schema in provider.get_tool_schemas():
            name = schema.get("name", "")
            if name:
                self._tool_to_provider[name] = provider

    def initialize_all(self, session_id: str, **kwargs) -> None:
        for p in self._providers:
            try:
                p.initialize(session_id, **kwargs)
            except Exception as e:
                logger.error("Failed to initialize memory provider %s: %s", p.name, e)

    def build_system_prompt(self) -> str:
        """Collect system prompt blocks from all providers."""
        blocks = []
        for p in self._providers:
            try:
                block = p.system_prompt_block()
                if block:
                    blocks.append(block)
            except Exception as e:
                logger.error("Memory provider %s system_prompt error: %s", p.name, e)
        return "\n\n".join(blocks)

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context from all providers."""
        parts = []
        for p in self._providers:
            try:
                result = p.prefetch(query, session_id=session_id)
                if result:
                    parts.append(result)
            except Exception as e:
                logger.error("Memory provider %s prefetch error: %s", p.name, e)
        return "\n\n".join(parts)

    def sync_all(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        for p in self._providers:
            try:
                p.sync_turn(user_content, assistant_content, session_id=session_id)
            except Exception as e:
                logger.error("Memory provider %s sync error: %s", p.name, e)

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for p in self._providers:
            try:
                schemas.extend(p.get_tool_schemas())
            except Exception as e:
                logger.error("Memory provider %s tool_schemas error: %s", p.name, e)
        return schemas

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tool_to_provider

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        provider = self._tool_to_provider.get(tool_name)
        if not provider:
            return json.dumps({"success": False, "error": f"No provider for tool {tool_name}"})
        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            logger.error("Memory tool %s error: %s", tool_name, e)
            return json.dumps({"success": False, "error": str(e)})

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Collect insights from messages about to be discarded by compression."""
        parts = []
        for p in self._providers:
            try:
                text = p.on_pre_compress(messages)
                if text:
                    parts.append(text)
            except Exception as e:
                logger.error("Memory provider %s on_pre_compress error: %s", p.name, e)
        return "\n\n".join(parts)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        for p in self._providers:
            try:
                p.on_session_end(messages)
            except Exception as e:
                logger.error("Memory provider %s session_end error: %s", p.name, e)

    def shutdown_all(self) -> None:
        for p in self._providers:
            try:
                p.shutdown()
            except Exception as e:
                logger.error("Memory provider %s shutdown error: %s", p.name, e)
