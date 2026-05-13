"""Zhihu API service - wraps official hackathon APIs.

OAuth endpoints use openapi.zhihu.com (per official docs).
Developer data APIs use developer.zhihu.com with Bearer auth.
"""
import time
import httpx
from typing import Any
from app.config import settings


class ZhihuService:
    def __init__(self):
        self.oauth_base = settings.ZHIHU_OAUTH_BASE_URL   # openapi.zhihu.com
        self.community_base = settings.ZHIHU_COMMUNITY_BASE_URL
        self.dev_base = settings.ZHIHU_DEV_BASE_URL

    def _dev_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.ZHIHU_DEV_TOKEN}",
            "X-Request-Timestamp": str(int(time.time())),
        }

    def _oauth_headers(self, access_token: str = "") -> dict:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    # ── OAuth ────────────────────────────────────────────────────────
    async def exchange_oauth_token(self, code: str, redirect_uri: str) -> dict:
        """Step 3: Exchange authorization code for access_token.
        POST https://openapi.zhihu.com/access_token
        """
        url = f"{self.oauth_base}/access_token"
        payload = {
            "app_id": settings.ZHIHU_APP_ID,
            "app_key": settings.ZHIHU_APP_KEY,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            # Zhihu OAuth token endpoint expects form-encoded payload.
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and not data.get("access_token") and not data.get("token"):
                raise ValueError(f"OAuth token exchange failed: {data}")
            return data

    async def get_user_info(self, access_token: str) -> dict:
        """Step 4: Get current user profile with access_token in Authorization header."""
        url = f"{self.oauth_base}/user"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._oauth_headers(access_token))
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("code") and data.get("code") != 0:
                raise ValueError(f"Get user info failed: {data}")
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]
            return data

    # ── Developer Data APIs ──────────────────────────────────────────
    async def get_hot_list(self, limit: int = 30) -> dict:
        """Fetch Zhihu hot list from developer API.
        Uses Bearer auth + X-Request-Timestamp per official docs.
        Limit max 30.
        """
        url = f"{self.dev_base}/api/v1/content/hot_list"
        params = {"Limit": min(limit, 30)}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._dev_headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def search_zhihu(self, query: str, limit: int = 10) -> dict:
        """Search Zhihu content to enrich AI context."""
        url = f"{self.dev_base}/api/v1/content/zhihu_search"
        params = {"q": query, "limit": limit}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._dev_headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def search_global(self, query: str, limit: int = 10) -> dict:
        """Search global web content."""
        url = f"{self.dev_base}/api/v1/content/global_search"
        params = {"q": query, "limit": limit}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._dev_headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def zhida_chat(self, messages: list[dict]) -> dict:
        """Call Zhihu Zhida Agent API for AI-powered Q&A."""
        url = f"{self.dev_base}/v1/chat/completions"
        payload = {"messages": messages, "model": "zhida"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._dev_headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    # ── Social / OAuth-based APIs ──────────────────────────────────
    def _parse_social_page(
        self, data: Any, page: int, per_page: int
    ) -> dict[str, Any]:
        fallback_page_size = min(per_page, 10)
        items: list[dict[str, Any]] = []
        paging: dict[str, Any] = {}

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            raw_items = data.get("data", [])
            items = raw_items if isinstance(raw_items, list) else []
            raw_paging = data.get("paging", {})
            paging = raw_paging if isinstance(raw_paging, dict) else {}

        total = paging.get("totals")
        if isinstance(total, str) and total.isdigit():
            total = int(total)
        if not isinstance(total, int):
            total = None

        if "is_end" in paging:
            is_end = bool(paging.get("is_end"))
        else:
            is_end = len(items) < fallback_page_size

        has_more = not is_end
        next_page = page + 1 if has_more else None

        return {
            "items": items,
            "page": page,
            "per_page": per_page,
            "items_count": len(items),
            "has_more": has_more,
            "is_end": is_end,
            "next_page": next_page,
            "total": total,
        }

    async def get_followees(self, access_token: str, page: int = 0, per_page: int = 20) -> dict[str, Any]:
        """Get list of users the current user follows with pagination metadata."""
        url = f"{self.oauth_base}/user/followees"
        params = {"page": page, "per_page": per_page}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url, headers=self._oauth_headers(access_token), params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_social_page(data, page, per_page)

    async def get_followers(self, access_token: str, page: int = 0, per_page: int = 20) -> dict[str, Any]:
        """Get current user's followers list with pagination metadata."""
        url = f"{self.oauth_base}/user/followers"
        params = {"page": page, "per_page": per_page}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url, headers=self._oauth_headers(access_token), params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_social_page(data, page, per_page)

    async def get_followers_count(self, access_token: str) -> int:
        """Get full follower count for snapshotting."""
        first_page = await self.get_followers(access_token, page=0, per_page=50)
        if isinstance(first_page.get("total"), int):
            return int(first_page["total"])

        items = first_page.get("items", [])
        total = len(items) if isinstance(items, list) else 0
        page = first_page.get("next_page")
        has_more = bool(first_page.get("has_more"))
        max_pages = 200
        page_count = 1

        while has_more and isinstance(page, int) and page_count < max_pages:
            current = await self.get_followers(access_token, page=page, per_page=50)
            current_items = current.get("items", [])
            if not isinstance(current_items, list) or len(current_items) == 0:
                break
            total += len(current_items)
            has_more = bool(current.get("has_more"))
            page = current.get("next_page")
            page_count += 1

        return total

    async def get_moments(self, access_token: str) -> list:
        """Get the current user's follow feed (moments)."""
        url = f"{self.oauth_base}/user/moments"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._oauth_headers(access_token))
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("data", [])

    async def publish_pin(self, access_token: str, content: str) -> dict:
        """Publish a pin (想法) to Zhihu circle.
        Uses the OAuth access_token for the user.
        """
        url = f"{self.community_base}/publish/pin"
        payload = {"content": content}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url, headers=self._oauth_headers(access_token), json=payload
            )
            resp.raise_for_status()
            return resp.json()


zhihu_service = ZhihuService()
