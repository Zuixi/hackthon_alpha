"""Shared types for normalized provider responses."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A normalized tool call from any provider."""

    id: str | None
    name: str
    arguments: str  # JSON string

    @property
    def type(self) -> str:
        return "function"

    @property
    def function(self) -> ToolCall:
        return self

    def parsed_arguments(self) -> dict:
        try:
            return json.loads(self.arguments)
        except (json.JSONDecodeError, TypeError):
            return {}


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class NormalizedResponse:
    """Normalized API response from any provider."""

    content: str | None
    tool_calls: list[ToolCall] | None
    finish_reason: str  # "stop", "tool_calls", "length"
    reasoning: str | None = None
    usage: Usage | None = None


def build_tool_call(
    id: str | None,
    name: str,
    arguments: Any,
) -> ToolCall:
    args_str = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
    return ToolCall(id=id, name=name, arguments=args_str)


def map_finish_reason(reason: str | None, mapping: dict[str, str]) -> str:
    if reason is None:
        return "stop"
    return mapping.get(reason, "stop")
