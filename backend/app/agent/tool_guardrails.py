"""Tool call guardrails — detect and break infinite loops.

Two mechanisms:
  1. Repeated call detection: same tool + same args called N times → inject warning
  2. Consecutive error circuit breaker: M errors in a row → halt tool usage
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolGuardrails:
    """Monitors tool call patterns to prevent infinite loops."""

    def __init__(
        self,
        max_repeat: int = 3,
        max_consecutive_errors: int = 5,
        history_window: int = 10,
    ):
        self.max_repeat = max_repeat
        self.max_consecutive_errors = max_consecutive_errors
        self._history_window = history_window
        self._call_history: List[str] = []
        self._consecutive_errors = 0
        self._halted = False

    def _make_hash(self, name: str, args: Any) -> str:
        args_str = json.dumps(args, sort_keys=True, ensure_ascii=False) if isinstance(args, dict) else str(args)
        return hashlib.md5(f"{name}:{args_str}".encode()).hexdigest()

    def check_before_execute(self, name: str, args: Any) -> Optional[str]:
        """Return a warning/halt message if a guardrail triggers, else None."""
        if self._halted:
            return (
                f"Tool execution halted after {self.max_consecutive_errors} consecutive errors. "
                "Please try a different approach or ask the user for clarification."
            )

        if self._consecutive_errors >= self.max_consecutive_errors:
            self._halted = True
            return (
                f"Tool execution halted: {self._consecutive_errors} consecutive errors detected. "
                "Stopping tool calls to avoid further issues. "
                "Summarize what you've accomplished and ask the user for guidance."
            )

        call_hash = self._make_hash(name, args)
        window = self._call_history[-self._history_window:]
        repeat_count = sum(1 for h in window if h == call_hash)

        if repeat_count >= self.max_repeat:
            return (
                f"Tool '{name}' has been called {repeat_count} times with identical arguments "
                f"in the last {self._history_window} calls. This looks like an infinite loop. "
                "Try a different approach, different arguments, or ask the user for help."
            )

        self._call_history.append(call_hash)
        if len(self._call_history) > self._history_window * 2:
            self._call_history = self._call_history[-self._history_window:]

        return None

    def record_error(self) -> None:
        self._consecutive_errors += 1

    def record_success(self) -> None:
        self._consecutive_errors = 0

    def reset(self) -> None:
        self._call_history.clear()
        self._consecutive_errors = 0
        self._halted = False
