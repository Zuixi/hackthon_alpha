"""NewsNow aggregation API fetcher for multi-platform hot topics.

API: GET https://newsnow.busiyi.world/api/s?id=<platform_id>&latest
Response: {"status": "success|cache", "items": [{"title", "url", "mobileUrl"}]}
"""
import asyncio
import logging
import random
from typing import Any
from urllib.parse import urlparse, urlencode, parse_qs

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PLATFORM_REGISTRY: list[dict[str, str]] = [
    {"id": "zhihu", "name": "知乎", "platform_key": "zhihu"},
    {"id": "weibo", "name": "微博热搜", "platform_key": "weibo"},
    {"id": "douyin", "name": "抖音热点", "platform_key": "douyin"},
    {"id": "toutiao", "name": "今日头条", "platform_key": "toutiao"},
    {"id": "bilibili-hot-search", "name": "B站热搜", "platform_key": "bilibili"},
    {"id": "baidu", "name": "百度热搜", "platform_key": "baidu"},
    {"id": "thepaper", "name": "澎湃新闻", "platform_key": "thepaper"},
    {"id": "tieba", "name": "贴吧", "platform_key": "tieba"},
]

PLATFORM_NAMES: dict[str, str] = {
    **{p["platform_key"]: p["name"] for p in PLATFORM_REGISTRY},
}

_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "source", "from", "timestamp", "t", "s",
    "band_rank", "Refer", "sudaref", "display",
}

MAX_RETRIES = 2
REQUEST_TIMEOUT = 15
INTER_PLATFORM_DELAY = 2.0


def normalize_url(url: str) -> str:
    """Strip tracking parameters for cleaner URLs."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=False)
        cleaned = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
        new_query = urlencode(cleaned, doseq=True) if cleaned else ""
        return parsed._replace(query=new_query, fragment="").geturl()
    except Exception:
        return url


def clean_title(raw: Any) -> str | None:
    """Return cleaned title string or None if invalid."""
    if raw is None or isinstance(raw, float):
        return None
    title = str(raw).strip()
    return title if title else None


async def fetch_platform(platform_id: str) -> list[dict[str, str]]:
    """Fetch hot items for a single platform from NewsNow API with retries."""
    url = f"{settings.NEWSNOW_API_URL}?id={platform_id}&latest"

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url, headers={
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://newsnow.busiyi.world/",
                })

            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")

            data = resp.json()
            status = data.get("status", "")
            if status not in ("success", "cache"):
                raise ValueError(f"unexpected status: {status}")

            items: list[dict[str, str]] = []
            for raw_item in data.get("items", []):
                title = clean_title(raw_item.get("title"))
                if not title:
                    continue
                items.append({
                    "title": title,
                    "url": normalize_url(raw_item.get("url", "")),
                    "mobile_url": raw_item.get("mobileUrl", ""),
                })

            logger.info("NewsNow [%s] fetched %d items (attempt %d)", platform_id, len(items), attempt)
            return items

        except Exception as e:
            if attempt <= MAX_RETRIES:
                wait = random.uniform(2, 4) + (attempt - 1)
                logger.warning("NewsNow [%s] attempt %d failed: %s, retry in %.1fs", platform_id, attempt, e, wait)
                await asyncio.sleep(wait)
            else:
                logger.error("NewsNow [%s] all %d attempts failed: %s", platform_id, attempt, e)
                return []

    return []


async def fetch_all_platforms(exclude_platform_keys: set[str] | None = None) -> dict[str, list[dict[str, str]]]:
    """Fetch hot items from all configured NewsNow platforms sequentially
    with inter-platform delay to avoid rate limiting.

    Returns mapping of platform_key -> items list.
    """
    results: dict[str, list[dict[str, str]]] = {}
    excluded = exclude_platform_keys or set()
    selected_platforms = [p for p in PLATFORM_REGISTRY if p["platform_key"] not in excluded]

    for i, platform in enumerate(selected_platforms):
        pid = platform["id"]
        pkey = platform["platform_key"]
        items = await fetch_platform(pid)
        if items:
            results[pkey] = items

        if i < len(selected_platforms) - 1:
            await asyncio.sleep(INTER_PLATFORM_DELAY)

    logger.info(
        "NewsNow fetch complete: %d/%d platforms succeeded",
        len(results), len(selected_platforms),
    )
    return results
