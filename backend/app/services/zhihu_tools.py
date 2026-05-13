"""Zhihu API tool functions for Agent tool-calling.

Each function is a self-contained tool that the Agent can invoke.
They return JSON-serializable results for the model to reason about.

Two auth modes:
  - Developer Data APIs (hot_list, search, direct_answer): x-api-key header
  - Community APIs (ring, publish, comment, reaction): HMAC-SHA256 signed headers
"""
import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DEV_BASE = settings.ZHIHU_DEV_BASE_URL or "https://developer.zhihu.com"
_COMMUNITY_BASE = settings.ZHIHU_COMMUNITY_BASE_URL or "https://openapi.zhihu.com"

_hot_list_cache: dict[str, Any] = {"data": None, "ts": 0}
_search_cache: dict[str, Any] = {}
HOT_CACHE_TTL = 3600
SEARCH_CACHE_TTL = 600


def _dev_headers() -> dict[str, str]:
    dev_token = (
        getattr(settings, "ZHIHU_DEV_API_KEY", "")
        or getattr(settings, "ZHIHU_ACCESS_SECRET", "")
        or getattr(settings, "ZHIHU_DEV_TOKEN", "")
    )
    if not dev_token:
        raise ValueError("开发者 API 凭证未配置 (ZHIHU_DEV_API_KEY / ZHIHU_ACCESS_SECRET)")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {dev_token}",
        "X-Request-Timestamp": str(int(time.time())),
    }


def _community_sign_headers(app_key: str, app_secret: str) -> dict[str, str]:
    ts = str(int(time.time()))
    log_id = f"req_{uuid.uuid4().hex[:16]}"
    extra_info = ""
    sign_str = f"app_key:{app_key}|ts:{ts}|logid:{log_id}|extra_info:{extra_info}"
    signature = base64.b64encode(
        hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "X-App-Key": app_key,
        "X-Timestamp": ts,
        "X-Log-Id": log_id,
        "X-Sign": signature,
        "X-Extra-Info": extra_info,
        "Content-Type": "application/json",
    }


def _get_community_headers() -> dict[str, str]:
    app_key = getattr(settings, "ZHIHU_COMMUNITY_APP_KEY", "") or ""
    app_secret = getattr(settings, "ZHIHU_COMMUNITY_APP_SECRET", "") or ""
    if not app_key or not app_secret:
        raise ValueError("社区 API 凭证未配置 (ZHIHU_COMMUNITY_APP_KEY / ZHIHU_COMMUNITY_APP_SECRET)")
    return _community_sign_headers(app_key, app_secret)


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "zhihu_hot_list",
        "description": "获取知乎实时热榜列表。返回热门话题的标题、热度分值、优质回答摘要等信息。每日限100次，有缓存。",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "获取最近N小时的热榜，默认24",
                    "default": 24,
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认20，最多50",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
    {
        "name": "zhihu_search",
        "description": "搜索知乎站内内容。返回文章和问答的标题、摘要、作者、点赞数等。适合查找特定话题的已有讨论。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认10",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "zhihu_global_search",
        "description": "搜索全网内容。返回网页标题、摘要、来源等。适合获取知乎站外的相关信息作为创作素材。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认10",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "zhihu_direct_answer",
        "description": "调用知乎直答Agent，基于知乎海量优质内容快速生成精准、可信的回答。适合需要引用知乎已有内容来丰富创作素材的场景。",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "要提问的问题",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "zhihu_get_ring_detail",
        "description": "获取知乎圈子的详情和最新帖子列表。可以查看圈子里其他人在讨论什么。",
        "input_schema": {
            "type": "object",
            "properties": {
                "ring_id": {
                    "type": "string",
                    "description": "圈子ID。可用圈子：2001009660925334090(OpenClaw人类观察员)、2015023739549529606(A2A for Reconnect)、2029619126742656657(黑客松脑洞补给站)",
                    "default": "2029619126742656657",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，最多50",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
    {
        "name": "zhihu_publish_pin",
        "description": "在知乎圈子中发布一条想法。用户确认后才能调用。每小时最多5条。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "想法正文内容",
                },
                "ring_id": {
                    "type": "string",
                    "description": "目标圈子ID，默认为黑客松脑洞补给站",
                    "default": "2029619126742656657",
                },
                "title": {
                    "type": "string",
                    "description": "标题（可选）",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "zhihu_create_comment",
        "description": "在知乎圈子的想法下创建评论或回复。每小时每个想法下最多20条。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_token": {
                    "type": "string",
                    "description": "想法ID或评论ID",
                },
                "content_type": {
                    "type": "string",
                    "description": "内容类型：pin(对想法评论)或comment(回复评论)",
                    "enum": ["pin", "comment"],
                },
                "content": {
                    "type": "string",
                    "description": "评论内容",
                },
            },
            "required": ["content_token", "content_type", "content"],
        },
    },
    {
        "name": "zhihu_reaction",
        "description": "对知乎圈子中的想法或评论进行点赞/取消点赞。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_token": {
                    "type": "string",
                    "description": "想法ID或评论ID",
                },
                "content_type": {
                    "type": "string",
                    "description": "内容类型：pin(想法)或comment(评论)",
                    "enum": ["pin", "comment"],
                },
                "action_value": {
                    "type": "integer",
                    "description": "1=点赞，0=取消点赞",
                    "enum": [0, 1],
                },
            },
            "required": ["content_token", "content_type", "action_value"],
        },
    },
    {
        "name": "zhihu_get_comments",
        "description": "获取想法的评论列表或评论的回复列表。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_token": {
                    "type": "string",
                    "description": "想法ID或评论ID",
                },
                "content_type": {
                    "type": "string",
                    "description": "内容类型：pin(想法的评论)或comment(评论的回复)",
                    "enum": ["pin", "comment"],
                },
                "page_num": {
                    "type": "integer",
                    "description": "页码，默认1",
                    "default": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认10，最多50",
                    "default": 10,
                },
            },
            "required": ["content_token", "content_type"],
        },
    },
    {
        "name": "zhihu_story_list",
        "description": "获取知乎故事（会员小说）内容库的故事概要列表。包含故事标题、简介、标签等。",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "zhihu_story_detail",
        "description": "获取知乎故事的章节详情，包含作者、导语和正文（最多3000字）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "work_id": {
                    "type": "string",
                    "description": "故事作品ID",
                },
            },
            "required": ["work_id"],
        },
    },
]


async def zhihu_hot_list(hours: int = 24, limit: int = 20) -> dict:
    """获取知乎实时热榜。"""
    now = time.time()
    if _hot_list_cache["data"] and (now - _hot_list_cache["ts"]) < HOT_CACHE_TTL:
        return _hot_list_cache["data"]

    url = f"{_DEV_BASE}/api/v1/content/hot_list"
    params = {"hours": hours, "limit": min(limit, 50)}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_dev_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            _hot_list_cache["data"] = data
            _hot_list_cache["ts"] = now
            return data
    except Exception as e:
        logger.error("zhihu_hot_list error: %s", e)
        return {"error": str(e)}


async def zhihu_search(query: str, limit: int = 10) -> dict:
    """搜索知乎站内内容。"""
    cache_key = f"zhihu:{query}:{limit}"
    cached = _search_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < SEARCH_CACHE_TTL:
        return cached["data"]

    url = f"{_DEV_BASE}/api/v1/content/zhihu_search"
    params = {"Query": query, "limit": min(limit, 20)}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_dev_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            _search_cache[cache_key] = {"data": data, "ts": time.time()}
            return data
    except Exception as e:
        logger.error("zhihu_search error: %s", e)
        return {"error": str(e)}


async def zhihu_global_search(query: str, limit: int = 10) -> dict:
    """搜索全网内容。"""
    cache_key = f"global:{query}:{limit}"
    cached = _search_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < SEARCH_CACHE_TTL:
        return cached["data"]

    url = f"{_DEV_BASE}/api/v1/content/global_search"
    params = {"Query": query, "limit": min(limit, 20)}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_dev_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            _search_cache[cache_key] = {"data": data, "ts": time.time()}
            return data
    except Exception as e:
        logger.error("zhihu_global_search error: %s", e)
        return {"error": str(e)}


async def zhihu_direct_answer(question: str) -> dict:
    """调用知乎直答Agent。"""
    url = f"{_DEV_BASE}/v1/chat/completions"
    payload = {
        "messages": [{"role": "user", "content": question}],
        "model": "zhida",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=_dev_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                answer = choices[0].get("message", {}).get("content", "")
                return {"answer": answer, "raw": data}
            return data
    except Exception as e:
        logger.error("zhihu_direct_answer error: %s", e)
        return {"error": str(e)}


async def zhihu_get_ring_detail(ring_id: str = "2029619126742656657", page_size: int = 20) -> dict:
    """获取圈子详情和帖子列表。"""
    url = f"{_COMMUNITY_BASE}/openapi/ring/detail"
    params = {"ring_id": ring_id, "page_size": min(page_size, 50), "page_num": 1}
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_get_ring_detail error: %s", e)
        return {"error": str(e)}


async def zhihu_publish_pin(
    content: str,
    ring_id: str = "2029619126742656657",
    title: str = "",
    image_urls: list[str] | None = None,
) -> dict:
    """在圈子发布想法。"""
    url = f"{_COMMUNITY_BASE}/openapi/publish/pin"
    payload: dict[str, Any] = {"content": content, "ring_id": ring_id}
    if title:
        payload["title"] = title
    if image_urls:
        payload["image_urls"] = image_urls
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_publish_pin error: %s", e)
        return {"error": str(e)}


async def zhihu_create_comment(
    content_token: str, content_type: str, content: str
) -> dict:
    """创建评论/回复。"""
    url = f"{_COMMUNITY_BASE}/openapi/comment/create"
    payload = {
        "content_token": content_token,
        "content_type": content_type,
        "content": content,
    }
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_create_comment error: %s", e)
        return {"error": str(e)}


async def zhihu_reaction(
    content_token: str, content_type: str, action_value: int
) -> dict:
    """点赞/取消点赞。"""
    url = f"{_COMMUNITY_BASE}/openapi/reaction"
    payload = {
        "content_token": content_token,
        "content_type": content_type,
        "action_type": "like",
        "action_value": action_value,
    }
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_reaction error: %s", e)
        return {"error": str(e)}


async def zhihu_get_comments(
    content_token: str, content_type: str, page_num: int = 1, page_size: int = 10
) -> dict:
    """获取评论列表。"""
    url = f"{_COMMUNITY_BASE}/openapi/comment/list"
    params = {
        "content_token": content_token,
        "content_type": content_type,
        "page_num": page_num,
        "page_size": min(page_size, 50),
    }
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_get_comments error: %s", e)
        return {"error": str(e)}


async def zhihu_story_list() -> dict:
    """获取故事列表。"""
    url = f"{_COMMUNITY_BASE}/openapi/hackathon_story/list"
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_story_list error: %s", e)
        return {"error": str(e)}


async def zhihu_story_detail(work_id: str) -> dict:
    """获取故事详情。"""
    url = f"{_COMMUNITY_BASE}/openapi/hackathon_story/detail"
    params = {"work_id": work_id}
    try:
        headers = _get_community_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("zhihu_story_detail error: %s", e)
        return {"error": str(e)}


SUPPORTED_PLATFORMS = [
    "zhihu", "weibo", "bilibili", "douyin",
    "toutiao", "baidu", "36kr", "ithome",
]


async def hot_topics_multiplatform(platform: str = "", limit: int = 20) -> dict:
    """获取多平台热点话题（来自数据库，由后台调度器定期采集）。"""
    from app.database import SessionLocal
    from app.models.hot_topic import HotTopic
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        query = db.query(HotTopic)
        if platform:
            query = query.filter(HotTopic.platform == platform.lower())
        topics = (
            query.order_by(desc(HotTopic.fetched_at), desc(HotTopic.hot_score))
            .limit(min(limit, 50))
            .all()
        )
        items = []
        for t in topics:
            items.append({
                "id": t.id,
                "title": t.title,
                "platform": t.platform,
                "hot_score": t.hot_score,
                "url": t.url or "",
                "excerpt": (t.excerpt or "")[:150],
            })
        return {
            "platform": platform or "all",
            "total": len(items),
            "items": items,
        }
    except Exception as e:
        logger.error("hot_topics_multiplatform error: %s", e)
        return {"error": str(e)}
    finally:
        db.close()


async def hot_topics_grouped(platform: str = "") -> dict:
    """按关键词分组的热点话题，便于分析特定领域的热点分布。"""
    from app.database import SessionLocal
    from app.models.hot_topic import HotTopic
    from app.services.keyword_filter import get_keyword_rules, group_topics_by_keywords
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        query = db.query(HotTopic)
        if platform:
            query = query.filter(HotTopic.platform == platform.lower())
        topics = (
            query.order_by(desc(HotTopic.fetched_at), desc(HotTopic.hot_score))
            .limit(200)
            .all()
        )
        topic_dicts = [
            {"id": t.id, "title": t.title, "platform": t.platform,
             "hot_score": t.hot_score, "url": t.url or ""}
            for t in topics
        ]

        word_groups, filter_words, global_filters = get_keyword_rules()
        grouped, unmatched = group_topics_by_keywords(
            topic_dicts, word_groups, filter_words, global_filters
        )

        result_groups = {}
        for group_name, group_topics in grouped.items():
            result_groups[group_name] = {
                "count": len(group_topics),
                "topics": group_topics[:10],
            }

        return {
            "platform": platform or "all",
            "groups": result_groups,
            "unmatched_count": len(unmatched),
        }
    except Exception as e:
        logger.error("hot_topics_grouped error: %s", e)
        return {"error": str(e)}
    finally:
        db.close()


MULTIPLATFORM_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "hot_topics_multiplatform",
        "description": (
            "获取多平台热点话题。支持知乎、微博、B站、抖音、头条、百度等平台。"
            "不指定平台则返回全平台热点。可用于跨平台热点对比分析。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": f"平台名称，可选值: {', '.join(SUPPORTED_PLATFORMS)}。留空返回全平台。",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认20，最多50",
                    "default": 20,
                },
            },
            "required": [],
        },
    },
    {
        "name": "hot_topics_grouped",
        "description": (
            "按关键词分组的热点话题。将热点按预设的领域关键词（如科技、财经、娱乐等）自动分组，"
            "便于快速了解特定领域的热点分布和趋势。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": f"平台名称，可选值: {', '.join(SUPPORTED_PLATFORMS)}。留空为全平台。",
                },
            },
            "required": [],
        },
    },
]


TOOL_DISPATCH: dict[str, Any] = {
    "zhihu_hot_list": zhihu_hot_list,
    "zhihu_search": zhihu_search,
    "zhihu_global_search": zhihu_global_search,
    "zhihu_direct_answer": zhihu_direct_answer,
    "zhihu_get_ring_detail": zhihu_get_ring_detail,
    "zhihu_publish_pin": zhihu_publish_pin,
    "zhihu_create_comment": zhihu_create_comment,
    "zhihu_reaction": zhihu_reaction,
    "zhihu_get_comments": zhihu_get_comments,
    "zhihu_story_list": zhihu_story_list,
    "zhihu_story_detail": zhihu_story_detail,
    "hot_topics_multiplatform": hot_topics_multiplatform,
    "hot_topics_grouped": hot_topics_grouped,
}


async def dispatch_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call by name with given arguments, return JSON string."""
    func = TOOL_DISPATCH.get(name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
    try:
        result = await func(**arguments)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("Tool dispatch error for %s: %s", name, e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)
