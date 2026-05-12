import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from app.database import get_db
from app.models.hot_topic import HotTopic
from app.schemas.hot import (
    HotTopicResponse,
    HotTopicListResponse,
    HotBatchResponse,
    HotDayGroup,
    HotHistoryResponse,
)
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/api/hot", tags=["hot"])
logger = logging.getLogger(__name__)

CACHE_KEY = "hot:latest"
CACHE_TTL_SECONDS = 300

DATA_RETENTION_DAYS = 5


@router.get("", response_model=HotTopicListResponse)
async def get_hot_topics(limit: int = 30, db: Session = Depends(get_db)):
    """Get the latest batch of hot topics from DB (populated by scheduler)."""
    cached = cache_get(CACHE_KEY)
    if cached is not None:
        items = cached[:limit]
        return HotTopicListResponse(items=items, total=len(items))

    latest_batch = (
        db.query(HotTopic.fetch_batch)
        .filter(HotTopic.fetch_batch != "")
        .order_by(HotTopic.fetched_at.desc())
        .limit(1)
        .scalar()
    )

    if not latest_batch:
        return HotTopicListResponse(items=[], total=0)

    db_topics = (
        db.query(HotTopic)
        .filter(HotTopic.fetch_batch == latest_batch)
        .order_by(HotTopic.hot_score.desc())
        .limit(limit)
        .all()
    )

    result = [HotTopicResponse.model_validate(t).model_dump() for t in db_topics]
    cache_set(CACHE_KEY, result, CACHE_TTL_SECONDS)

    return HotTopicListResponse(
        items=[HotTopicResponse(**r) for r in result],
        total=len(result),
    )


@router.get("/history", response_model=HotHistoryResponse)
async def get_hot_history(
    days: int = Query(default=5, ge=1, le=5),
    db: Session = Depends(get_db),
):
    """Get hot topics history grouped by day, up to 5 days."""
    cache_key = f"hot:history:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return HotHistoryResponse(**cached)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    topics = (
        db.query(HotTopic)
        .filter(HotTopic.fetched_at >= cutoff, HotTopic.fetch_batch != "")
        .order_by(HotTopic.fetched_at.desc())
        .all()
    )

    batch_map: dict[str, list[HotTopic]] = defaultdict(list)
    for t in topics:
        batch_map[t.fetch_batch].append(t)

    day_map: dict[str, list[HotBatchResponse]] = defaultdict(list)
    for batch_id, batch_topics in sorted(batch_map.items(), reverse=True):
        if not batch_topics:
            continue
        date_str = batch_topics[0].fetched_at.strftime("%Y-%m-%d")
        items = [HotTopicResponse.model_validate(t) for t in batch_topics]
        day_map[date_str].append(HotBatchResponse(
            fetch_batch=batch_id,
            fetched_at=batch_topics[0].fetched_at,
            items=items,
            count=len(items),
        ))

    day_groups = []
    for date_str in sorted(day_map.keys(), reverse=True):
        batches = day_map[date_str]
        topic_count = sum(b.count for b in batches)
        day_groups.append(HotDayGroup(
            date=date_str,
            batches=batches,
            topic_count=topic_count,
        ))

    result = HotHistoryResponse(days=day_groups, total_days=len(day_groups))
    cache_set(cache_key, result.model_dump(), CACHE_TTL_SECONDS)
    return result


@router.get("/{topic_id}", response_model=HotTopicResponse)
async def get_hot_topic(topic_id: str, db: Session = Depends(get_db)):
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic
