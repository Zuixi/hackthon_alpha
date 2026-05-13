"""Zhihu API tools — registered via ToolRegistry.

Wraps all Zhihu API functions from app.services.zhihu_tools and registers
them into the agent tool registry with proper schemas, including the
multiplatform hot topic tools.
"""

from app.agent.tools.registry import registry
from app.services.zhihu_tools import (
    TOOL_DEFINITIONS,
    MULTIPLATFORM_TOOL_DEFINITIONS,
    zhihu_hot_list,
    zhihu_search,
    zhihu_global_search,
    zhihu_direct_answer,
    zhihu_get_ring_detail,
    zhihu_publish_pin,
    zhihu_create_comment,
    zhihu_reaction,
    zhihu_get_comments,
    zhihu_story_list,
    zhihu_story_detail,
    hot_topics_multiplatform,
    hot_topics_grouped,
)

_HANDLERS = {
    "zhihu_hot_list": lambda args: zhihu_hot_list(**args),
    "zhihu_search": lambda args: zhihu_search(**args),
    "zhihu_global_search": lambda args: zhihu_global_search(**args),
    "zhihu_direct_answer": lambda args: zhihu_direct_answer(**args),
    "zhihu_get_ring_detail": lambda args: zhihu_get_ring_detail(**args),
    "zhihu_publish_pin": lambda args: zhihu_publish_pin(**args),
    "zhihu_create_comment": lambda args: zhihu_create_comment(**args),
    "zhihu_reaction": lambda args: zhihu_reaction(**args),
    "zhihu_get_comments": lambda args: zhihu_get_comments(**args),
    "zhihu_story_list": lambda args: zhihu_story_list(**args),
    "zhihu_story_detail": lambda args: zhihu_story_detail(**args),
    "hot_topics_multiplatform": lambda args: hot_topics_multiplatform(**args),
    "hot_topics_grouped": lambda args: hot_topics_grouped(**args),
}


def register_zhihu_tools() -> None:
    """Register all Zhihu API tools into the global registry."""
    all_defs = TOOL_DEFINITIONS + MULTIPLATFORM_TOOL_DEFINITIONS
    for tool_def in all_defs:
        name = tool_def["name"]
        handler = _HANDLERS.get(name)
        if handler is None:
            continue
        registry.register(
            name=name,
            schema=tool_def,
            handler=handler,
            is_async=True,
        )
