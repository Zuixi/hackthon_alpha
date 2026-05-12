import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_user
from app.models.user import User
from app.services.zhihu import zhihu_service
from app.services.cache import cache_get, cache_set
from app.schemas.social import (
    FolloweeResponse,
    FolloweeListResponse,
    MomentResponse,
    MomentListResponse,
)

router = APIRouter(prefix="/api/social", tags=["social"])
logger = logging.getLogger(__name__)

FOLLOWEE_CACHE_TTL = 300  # 5 minutes
MOMENT_CACHE_TTL = 180  # 3 minutes


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
        items = [FolloweeResponse(**item) for item in raw]
        result = FolloweeListResponse(items=items, total=len(items))
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
