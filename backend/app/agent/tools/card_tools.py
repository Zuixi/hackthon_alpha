"""Idea Card tools — let the agent create, list, and delete inspiration cards.

Cards are persisted in PostgreSQL via the IdeaCard model.
All operations are scoped to the current user_id which is injected at
registration time via closure.
"""

import json
import logging
from typing import Any

from app.agent.tools.registry import registry
from app.database import SessionLocal
from app.models.idea_card import IdeaCard

logger = logging.getLogger(__name__)

CARD_TOOL_DEFINITIONS = [
    {
        "name": "create_idea_card",
        "description": (
            "保存一条灵感卡片到数据库。当用户要求保存灵感或卡片时，你必须调用此工具来执行实际保存操作。"
            "仅在文字中描述'已保存'是无效的，必须通过此工具调用才能真正将卡片写入数据库。"
            "调用成功后会返回 card_id 作为保存成功的凭证。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "灵感卡片的正文内容，应包含完整的创作洞察或灵感记录",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表，如 ['AI', '科技', '热点分析']，便于分类检索",
                    "default": [],
                },
                "hot_topic_id": {
                    "type": "string",
                    "description": "关联的热点话题ID（可选），将卡片与特定热点关联",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "list_idea_cards",
        "description": (
            "查询用户已保存的灵感卡片列表。支持按标签筛选和关键词搜索。"
            "可以帮助用户回顾之前保存的创作灵感。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "按标签筛选，如 'AI'",
                },
                "search": {
                    "type": "string",
                    "description": "按内容关键词搜索",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认10，最多50",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "delete_idea_card",
        "description": "从数据库中删除一条灵感卡片。必须调用此工具才能真正执行删除，仅在文字中回复'已删除'不会生效。需要提供卡片ID。",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "要删除的灵感卡片ID",
                },
            },
            "required": ["card_id"],
        },
    },
]


def _make_card_handlers(user_id: str, session_id: str = ""):
    """Return tool handler functions bound to the given user/session context."""

    async def create_idea_card(args: dict) -> Any:
        content = args.get("content", "")
        if not content:
            return {"error": "content 不能为空"}
        tags = args.get("tags", [])
        hot_topic_id = args.get("hot_topic_id")

        db = SessionLocal()
        try:
            card = IdeaCard(
                user_id=user_id,
                content=content,
                tags=tags,
                hot_topic_id=hot_topic_id or None,
                chat_session_id=session_id or None,
            )
            db.add(card)
            db.commit()
            db.refresh(card)
            logger.info("Card created: %s for user %s", card.id, user_id)
            return {
                "success": True,
                "card_id": card.id,
                "content_preview": content[:100],
                "tags": tags,
                "message": "灵感卡片已保存！可在「灵感卡片」页面查看。",
            }
        except Exception as e:
            db.rollback()
            logger.error("create_idea_card error: %s", e)
            return {"error": str(e)}
        finally:
            db.close()

    async def list_idea_cards(args: dict) -> Any:
        tag = args.get("tag", "")
        search = args.get("search", "")
        limit = min(args.get("limit", 10), 50)

        db = SessionLocal()
        try:
            query = db.query(IdeaCard).filter(IdeaCard.user_id == user_id)
            if tag:
                query = query.filter(IdeaCard.tags.any(tag))
            if search:
                query = query.filter(IdeaCard.content.ilike(f"%{search}%"))
            cards = query.order_by(IdeaCard.created_at.desc()).limit(limit).all()

            items = []
            for c in cards:
                item = {
                    "id": c.id,
                    "content": c.content[:200] + ("..." if len(c.content) > 200 else ""),
                    "tags": c.tags or [],
                    "created_at": str(c.created_at),
                }
                if c.hot_topic:
                    item["hot_topic_title"] = c.hot_topic.title
                items.append(item)

            return {"total": len(items), "items": items}
        except Exception as e:
            logger.error("list_idea_cards error: %s", e)
            return {"error": str(e)}
        finally:
            db.close()

    async def delete_idea_card(args: dict) -> Any:
        card_id = args.get("card_id", "")
        if not card_id:
            return {"error": "card_id 不能为空"}

        db = SessionLocal()
        try:
            card = (
                db.query(IdeaCard)
                .filter(IdeaCard.id == card_id, IdeaCard.user_id == user_id)
                .first()
            )
            if not card:
                return {"error": "卡片不存在或无权操作"}
            db.delete(card)
            db.commit()
            return {"success": True, "message": "灵感卡片已删除"}
        except Exception as e:
            db.rollback()
            logger.error("delete_idea_card error: %s", e)
            return {"error": str(e)}
        finally:
            db.close()

    return {
        "create_idea_card": create_idea_card,
        "list_idea_cards": list_idea_cards,
        "delete_idea_card": delete_idea_card,
    }


def register_card_tools(user_id: str, session_id: str = "") -> None:
    """Register card tools bound to the given user context."""
    handlers = _make_card_handlers(user_id, session_id)
    for tool_def in CARD_TOOL_DEFINITIONS:
        name = tool_def["name"]
        handler = handlers.get(name)
        if handler:
            registry.register(
                name=name,
                schema=tool_def,
                handler=handler,
                is_async=True,
            )
