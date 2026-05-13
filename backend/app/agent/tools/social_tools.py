"""Social insight tools — let the agent access follower stats, followees, and moments.

Follower stats come from the local DB (SocialFollowerSnapshot).
Followees and moments require the user's zhihu_token and call ZhihuService.
"""

import logging
from datetime import date, timedelta
from typing import Any

from app.agent.tools.registry import registry
from app.database import SessionLocal
from app.models.social_follower_snapshot import SocialFollowerSnapshot
from app.services.zhihu import zhihu_service

logger = logging.getLogger(__name__)

SOCIAL_TOOL_DEFINITIONS = [
    {
        "name": "get_follower_stats",
        "description": (
            "获取用户的粉丝增长趋势统计。返回最近N天的粉丝数量变化，"
            "包括每日增减量。帮助用户了解内容表现对粉丝增长的影响。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "查询最近多少天的数据，默认30天",
                    "default": 30,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_followee_list",
        "description": (
            "获取用户的知乎关注列表。可以查看用户关注了哪些创作者，"
            "帮助了解用户的兴趣领域和内容偏好。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "页码，从0开始",
                    "default": 0,
                },
                "per_page": {
                    "type": "integer",
                    "description": "每页条数，默认20",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recent_moments",
        "description": (
            "获取用户关注的人最近发布的动态。了解关注圈子里在讨论什么话题，"
            "发现潜在的创作灵感和互动机会。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def _make_social_handlers(user_id: str, zhihu_token: str = ""):
    """Return tool handler functions bound to the user context."""

    async def get_follower_stats(args: dict) -> Any:
        days = min(max(args.get("days", 30), 1), 365)

        db = SessionLocal()
        try:
            since = date.today() - timedelta(days=days)
            snapshots = (
                db.query(SocialFollowerSnapshot)
                .filter(
                    SocialFollowerSnapshot.user_id == user_id,
                    SocialFollowerSnapshot.snapshot_date >= since,
                )
                .order_by(SocialFollowerSnapshot.snapshot_date.asc())
                .all()
            )

            if not snapshots:
                return {
                    "message": "暂无粉丝数据。粉丝数据每天晚上20:00自动采集。",
                    "data": [],
                }

            data_points = []
            prev_count = None
            for s in snapshots:
                delta = (s.follower_count - prev_count) if prev_count is not None else 0
                data_points.append({
                    "date": str(s.snapshot_date),
                    "count": s.follower_count,
                    "delta": delta,
                })
                prev_count = s.follower_count

            latest = snapshots[-1].follower_count
            earliest = snapshots[0].follower_count
            total_change = latest - earliest

            return {
                "current_followers": latest,
                "total_change": total_change,
                "period_days": days,
                "trend": "上升" if total_change > 0 else ("下降" if total_change < 0 else "持平"),
                "data_points": data_points[-30:],
            }
        except Exception as e:
            logger.error("get_follower_stats error: %s", e)
            return {"error": str(e)}
        finally:
            db.close()

    async def get_followee_list(args: dict) -> Any:
        if not zhihu_token:
            return {"error": "未绑定知乎账号，无法获取关注列表"}

        page = args.get("page", 0)
        per_page = min(args.get("per_page", 20), 50)

        try:
            result = await zhihu_service.get_followees(zhihu_token, page=page, per_page=per_page)
            items = result.get("items", [])
            formatted = []
            for u in items[:per_page]:
                formatted.append({
                    "name": u.get("fullname", u.get("name", "")),
                    "headline": u.get("headline", ""),
                    "gender": u.get("gender", ""),
                    "url": u.get("url", ""),
                })
            return {
                "followees": formatted,
                "total": result.get("total"),
                "has_more": result.get("has_more", False),
                "page": page,
            }
        except Exception as e:
            logger.error("get_followee_list error: %s", e)
            return {"error": f"获取关注列表失败: {e}"}

    async def get_recent_moments(args: dict) -> Any:
        if not zhihu_token:
            return {"error": "未绑定知乎账号，无法获取关注动态"}

        try:
            moments = await zhihu_service.get_moments(zhihu_token)
            formatted = []
            for m in moments[:20]:
                actor = m.get("actor", {})
                target = m.get("target", {})
                formatted.append({
                    "actor": actor.get("fullname", actor.get("name", "")),
                    "action": m.get("action_text", ""),
                    "time": m.get("action_time", ""),
                    "target_title": target.get("title", ""),
                    "target_excerpt": (target.get("excerpt", "") or "")[:150],
                })
            return {
                "moments_count": len(formatted),
                "moments": formatted,
            }
        except Exception as e:
            logger.error("get_recent_moments error: %s", e)
            return {"error": f"获取关注动态失败: {e}"}

    return {
        "get_follower_stats": get_follower_stats,
        "get_followee_list": get_followee_list,
        "get_recent_moments": get_recent_moments,
    }


def register_social_tools(user_id: str, zhihu_token: str = "") -> None:
    """Register social tools bound to the given user context."""
    handlers = _make_social_handlers(user_id, zhihu_token)
    for tool_def in SOCIAL_TOOL_DEFINITIONS:
        name = tool_def["name"]
        handler = handlers.get(name)
        if handler:
            registry.register(
                name=name,
                schema=tool_def,
                handler=handler,
                is_async=True,
            )
