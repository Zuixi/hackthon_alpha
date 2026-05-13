"""Token usage and cost tracking for agent sessions.

Records per-turn and per-session token consumption, supports cache-read
discount tracking, and provides session-level summaries.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TurnUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str = ""
    tool_calls: int = 0


class TokenUsageTracker:
    """Accumulates token usage per turn and provides session summaries."""

    def __init__(self):
        self._turns: List[TurnUsage] = []
        self._current_turn: TurnUsage = TurnUsage()

    def new_turn(self, model: str = "") -> None:
        if self._current_turn.input_tokens or self._current_turn.output_tokens:
            self._turns.append(self._current_turn)
        self._current_turn = TurnUsage(model=model)

    def record_usage(self, usage_event: Dict[str, Any]) -> None:
        self._current_turn.input_tokens += usage_event.get("prompt_tokens", 0)
        self._current_turn.output_tokens += usage_event.get("completion_tokens", 0)
        self._current_turn.cache_read_tokens += usage_event.get("cache_read_tokens", 0)
        self._current_turn.cache_creation_tokens += usage_event.get("cache_creation_tokens", 0)

    def record_tool_call(self) -> None:
        self._current_turn.tool_calls += 1

    def flush_turn(self) -> None:
        if self._current_turn.input_tokens or self._current_turn.output_tokens:
            self._turns.append(self._current_turn)
        self._current_turn = TurnUsage()

    def summary(self) -> Dict[str, Any]:
        self.flush_turn()
        total_in = sum(t.input_tokens for t in self._turns)
        total_out = sum(t.output_tokens for t in self._turns)
        total_cache = sum(t.cache_read_tokens for t in self._turns)
        total_tools = sum(t.tool_calls for t in self._turns)

        return {
            "turns": len(self._turns),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cache_read_tokens": total_cache,
            "total_tokens": total_in + total_out,
            "total_tool_calls": total_tools,
            "cache_hit_rate": (total_cache / total_in * 100) if total_in > 0 else 0,
        }

    def reset(self) -> None:
        self._turns.clear()
        self._current_turn = TurnUsage()
