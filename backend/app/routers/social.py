import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.social_follower_snapshot import SocialFollowerSnapshot
from app.services.zhihu import zhihu_service
from app.services.cache import cache_get, cache_set
from app.schemas.social import (
    FolloweeResponse,
    FolloweeListResponse,
    MomentResponse,
    MomentListResponse,
    SocialPageMeta,
    FollowerStatsResponse,
    FollowerSnapshotItem,
)

router = APIRouter(prefix="/api/social", tags=["social"])
logger = logging.getLogger(__name__)

FOLLOWEE_CACHE_TTL = 300  # 5 minutes
FOLLOWER_CACHE_TTL = 300  # 5 minutes
MOMENT_CACHE_TTL = 180  # 3 minutes
FOLLOWER_STATS_CACHE_TTL = 300  # 5 minutes


@router.get("/followees", response_model=FolloweeListResponse)
async def get_followees(
    page: int = Query(0, ge=0),
    per_page: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """Get the current user's follow list with Redis caching."""
    if not user.zhihu_token:
        raise HTTPException(status_code=400, detail="未绑定知乎账号，无法获取关注列表")

    cache_key = f"social:followees:{user.id}:{page}:{per_page}"
    cached = cache_get(cache_key)
    if cached is not None:
        return FolloweeListResponse(**cached)

    try:
        raw = await zhihu_service.get_followees(user.zhihu_token, page, per_page)
        items = [FolloweeResponse(**item) for item in raw["items"]]
        result = FolloweeListResponse(
            items=items,
            page=SocialPageMeta(
                page=raw["page"],
                per_page=raw["per_page"],
                items_count=raw["items_count"],
                has_more=raw["has_more"],
                is_end=raw["is_end"],
                next_page=raw["next_page"],
                total=raw["total"],
            ),
        )
        cache_set(cache_key, result.model_dump(), FOLLOWEE_CACHE_TTL)
        return result
    except Exception as e:
        logger.warning("Failed to fetch followees: %s", e)
        raise HTTPException(status_code=502, detail=f"获取关注列表失败: {e}")


@router.get("/moments", response_model=MomentListResponse)
async def get_moments(user: User = Depends(get_current_user)):
    """Get the current user's follow feed (moments) with Redis caching."""
    if not user.zhihu_token:
        raise HTTPException(status_code=400, detail="未绑定知乎账号，无法获取关注动态")

    cache_key = f"social:moments:{user.id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return MomentListResponse(**cached)

    try:
        raw = await zhihu_service.get_moments(user.zhihu_token)
        items = [MomentResponse(**item) for item in raw]
        result = MomentListResponse(items=items, total=len(items))
        cache_set(cache_key, result.model_dump(), MOMENT_CACHE_TTL)
        return result
    except Exception as e:
        logger.warning("Failed to fetch moments: %s", e)
        raise HTTPException(status_code=502, detail=f"获取关注动态失败: {e}")


@router.get("/followers", response_model=FolloweeListResponse)
async def get_followers(
    page: int = Query(0, ge=0),
    per_page: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """Get the current user's followers list with Redis caching."""
    if not user.zhihu_token:
        raise HTTPException(status_code=400, detail="未绑定知乎账号，无法获取粉丝列表")

    cache_key = f"social:followers:{user.id}:{page}:{per_page}"
    cached = cache_get(cache_key)
    if cached is not None:
        return FolloweeListResponse(**cached)

    try:
        raw = await zhihu_service.get_followers(user.zhihu_token, page, per_page)
        items = [FolloweeResponse(**item) for item in raw["items"]]
        result = FolloweeListResponse(
            items=items,
            page=SocialPageMeta(
                page=raw["page"],
                per_page=raw["per_page"],
                items_count=raw["items_count"],
                has_more=raw["has_more"],
                is_end=raw["is_end"],
                next_page=raw["next_page"],
                total=raw["total"],
            ),
        )
        cache_set(cache_key, result.model_dump(), FOLLOWER_CACHE_TTL)
        return result
    except Exception as e:
        logger.warning("Failed to fetch followers: %s", e)
        raise HTTPException(status_code=502, detail=f"获取粉丝列表失败: {e}")


@router.get("/followers/stats", response_model=FollowerStatsResponse)
async def get_follower_stats(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily follower count snapshots (refreshed at 20:00 Asia/Shanghai)."""
    cache_key = f"social:followers:stats:{user.id}:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return FollowerStatsResponse(**cached)

    rows = (
        db.query(SocialFollowerSnapshot)
        .filter(SocialFollowerSnapshot.user_id == user.id)
        .order_by(desc(SocialFollowerSnapshot.snapshot_date))
        .limit(days)
        .all()
    )

    ordered_rows = list(reversed(rows))
    items: list[FollowerSnapshotItem] = []
    prev_count: int | None = None
    for row in ordered_rows:
        delta = None if prev_count is None else row.follower_count - prev_count
        items.append(
            FollowerSnapshotItem(
                snapshot_date=row.snapshot_date,
                follower_count=row.follower_count,
                delta=delta,
                refreshed_at=row.refreshed_at,
            )
        )
        prev_count = row.follower_count

    latest_count = items[-1].follower_count if items else None
    result = FollowerStatsResponse(
        items=items,
        total_days=len(items),
        latest_count=latest_count,
    )
    cache_set(cache_key, result.model_dump(), FOLLOWER_STATS_CACHE_TTL)
    return result
