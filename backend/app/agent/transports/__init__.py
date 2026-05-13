"""Transport layer — provider-agnostic request/response normalization.

Usage:
    from app.agent.transports import get_transport
    transport = get_transport("minimax_anthropic")
"""

from app.agent.transports.types import (
    NormalizedResponse,
    ToolCall,
    Usage,
    build_tool_call,
    map_finish_reason,
)  # noqa: F401

_REGISTRY: dict = {}
_discovered: bool = False


def register_transport(api_mode: str, transport_cls: type) -> None:
    _REGISTRY[api_mode] = transport_cls


def get_transport(api_mode: str):
    """Get a transport instance for the given api_mode. Returns None if unregistered."""
    global _discovered
    if not _discovered:
        _discover_transports()
    cls = _REGISTRY.get(api_mode)
    if cls is None:
        _discover_transports()
        cls = _REGISTRY.get(api_mode)
    if cls is None:
        return None
    return cls()


def _discover_transports() -> None:
    global _discovered
    _discovered = True
    try:
        import app.agent.transports.minimax  # noqa: F401
    except ImportError:
        pass
    try:
        import app.agent.transports.chat_completions  # noqa: F401
    except ImportError:
        pass
