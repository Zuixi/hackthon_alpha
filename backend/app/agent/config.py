"""Agent-specific configuration."""

from pathlib import Path

from app.config import settings

AGENT_DATA_DIR = Path(getattr(settings, "AGENT_DATA_DIR", "./data"))
AGENT_MAX_ITERATIONS = int(getattr(settings, "AGENT_MAX_ITERATIONS", 8))

# Provider detection from existing settings
LLM_PROVIDER = getattr(settings, "LLM_PROVIDER", "minimax")
LLM_MODEL = getattr(settings, "LLM_MODEL", "") or settings.MINIMAX_MODEL or "abab6.5-chat"
LLM_API_KEY = getattr(settings, "LLM_API_KEY", "") or settings.MINIMAX_API_KEY
LLM_BASE_URL = getattr(settings, "LLM_BASE_URL", "") or "https://api.minimaxi.com/anthropic"

MCP_SERVERS_CONFIG = getattr(settings, "MCP_SERVERS_CONFIG", "")

# Skill engine
SKILL_AUTO_EXTRACT = getattr(settings, "SKILL_AUTO_EXTRACT", True)
SKILL_SIMILARITY_THRESHOLD = float(getattr(settings, "SKILL_SIMILARITY_THRESHOLD", 0.7))

# Memory system
MEMORY_AUTO_REVIEW: bool = getattr(settings, "MEMORY_AUTO_REVIEW", True)
MEMORY_NUDGE_INTERVAL: int = int(getattr(settings, "MEMORY_NUDGE_INTERVAL", 8))
MEMORY_CHAR_LIMIT: int = int(getattr(settings, "MEMORY_CHAR_LIMIT", 2200))
USER_CHAR_LIMIT: int = int(getattr(settings, "USER_CHAR_LIMIT", 1375))

# Error recovery
MAX_EMPTY_RETRIES: int = int(getattr(settings, "MAX_EMPTY_RETRIES", 3))
MAX_STREAM_RETRIES: int = int(getattr(settings, "MAX_STREAM_RETRIES", 2))

# Tool result management
TOOL_RESULT_INLINE_LIMIT: int = int(getattr(settings, "TOOL_RESULT_INLINE_LIMIT", 3000))
TOOL_RESULT_PERSIST_THRESHOLD: int = int(getattr(settings, "TOOL_RESULT_PERSIST_THRESHOLD", 8000))
TURN_TOTAL_BUDGET: int = int(getattr(settings, "TURN_TOTAL_BUDGET", 15000))

# Guardrails
TOOL_MAX_REPEAT: int = int(getattr(settings, "TOOL_MAX_REPEAT", 3))
TOOL_MAX_CONSECUTIVE_ERRORS: int = int(getattr(settings, "TOOL_MAX_CONSECUTIVE_ERRORS", 5))

# Parallel tool execution
PARALLEL_TOOL_ENABLED: bool = getattr(settings, "PARALLEL_TOOL_ENABLED", True)


def get_transport_mode() -> str:
    """Determine transport mode from provider setting."""
    provider = LLM_PROVIDER.lower()
    if provider in ("minimax", "minimax_anthropic"):
        return "minimax_anthropic"
    if provider in ("openai", "deepseek", "qwen", "chat_completions"):
        return "chat_completions"
    return "minimax_anthropic"
