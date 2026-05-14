import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func as sa_func
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.hot_topic import HotTopic
from app.schemas.hot import (
    HotTopicResponse,
    HotTopicListResponse,
    HotBatchResponse,
    HotDayGroup,
    HotHistoryResponse,
    PlatformInfo,
    PlatformListResponse,
    KeywordGroupResponse,
    GroupedHotResponse,
    SourceCount,
    ZhihuSourceStatusResponse,
)
from app.services.cache import cache_get, cache_set
from app.services.newsnow_fetcher import PLATFORM_NAMES, PLATFORM_REGISTRY
from app.services.keyword_filter import (
    get_keyword_rules,
    group_topics_by_keywords,
)

router = APIRouter(prefix="/api/hot", tags=["hot"])
logger = logging.getLogger(__name__)

CACHE_KEY = "hot:latest"
CACHE_TTL_SECONDS = 300
DATA_RETENTION_DAYS = 5

_PLATFORM_ORDER = {
    p["platform_key"]: idx for idx, p in enumerate(PLATFORM_REGISTRY)
}


def _enrich_platform_name(topic_resp: dict) -> dict:
    """Add platform_name to a topic response dict."""
    platform = topic_resp.get("platform", "zhihu")
    topic_resp["platform_name"] = PLATFORM_NAMES.get(platform, platform)
    return topic_resp


def _topic_to_response(t: HotTopic) -> HotTopicResponse:
    data = HotTopicResponse.model_validate(t).model_dump()
    data = _enrich_platform_name(data)
    return HotTopicResponse(**data)


def _parse_platforms(platform_param: str | None) -> list[str] | None:
    if not platform_param:
        return None
    platforms = [p.strip() for p in platform_param.split(",") if p.strip()]
    return platforms if platforms else None


@router.get("", response_model=HotTopicListResponse)
async def get_hot_topics(
    limit: int = Query(50, ge=1, le=200),
    platform: str = Query(None, description="Comma-separated platform filter"),
    db: Session = Depends(get_db),
):
    """Get the latest batch of hot topics, optionally filtered by platform."""
    platforms = _parse_platforms(platform)
    cache_key = f"hot:latest:{platform or 'all'}:{limit}"

    cached = cache_get(cache_key)
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

    query = db.query(HotTopic).filter(HotTopic.fetch_batch == latest_batch)

    if platforms:
        query = query.filter(HotTopic.platform.in_(platforms))

    platform_sort = case(
        _PLATFORM_ORDER,
        value=HotTopic.platform,
        else_=len(_PLATFORM_ORDER),
    )
    db_topics = query.order_by(platform_sort, HotTopic.hot_score.desc()).limit(limit).all()

    result = [_enrich_platform_name(HotTopicResponse.model_validate(t).model_dump()) for t in db_topics]
    cache_set(cache_key, result, CACHE_TTL_SECONDS)

    return HotTopicListResponse(
        items=[HotTopicResponse(**r) for r in result],
        total=len(result),
    )


@router.get("/platforms", response_model=PlatformListResponse)
async def get_platforms(db: Session = Depends(get_db)):
    """Get available platforms with their latest topic counts."""
    cache_key = "hot:platforms"
    cached = cache_get(cache_key)
    if cached is not None:
        return PlatformListResponse(**cached)

    latest_batch = (
        db.query(HotTopic.fetch_batch)
        .filter(HotTopic.fetch_batch != "")
        .order_by(HotTopic.fetched_at.desc())
        .limit(1)
        .scalar()
    )

    if not latest_batch:
        return PlatformListResponse(platforms=[])

    rows = (
        db.query(HotTopic.platform, sa_func.count(HotTopic.id))
        .filter(HotTopic.fetch_batch == latest_batch)
        .group_by(HotTopic.platform)
        .all()
    )

    platforms = [
        PlatformInfo(
            id=p_id,
            name=PLATFORM_NAMES.get(p_id, p_id),
            count=count,
        )
        for p_id, count in sorted(rows, key=lambda r: r[1], reverse=True)
    ]

    result = PlatformListResponse(platforms=platforms)
    cache_set(cache_key, result.model_dump(), CACHE_TTL_SECONDS)
    return result


@router.get("/source-status", response_model=ZhihuSourceStatusResponse)
async def get_zhihu_source_status(db: Session = Depends(get_db)):
    """Diagnose current Zhihu source based on latest batch records."""
    cache_key = "hot:source-status:zhihu"
    cached = cache_get(cache_key)
    if cached is not None:
        return ZhihuSourceStatusResponse(**cached)

    latest_batch = (
        db.query(HotTopic.fetch_batch)
        .filter(HotTopic.fetch_batch != "")
        .order_by(HotTopic.fetched_at.desc())
        .limit(1)
        .scalar()
    )

    if not latest_batch:
        result = ZhihuSourceStatusResponse(
            mode=settings.HOT_ZHIHU_SOURCE_MODE,
            latest_batch="",
            detected_source="unknown",
            total_topics=0,
            sources=[],
        )
        cache_set(cache_key, result.model_dump(), CACHE_TTL_SECONDS)
        return result

    rows = (
        db.query(HotTopic.source, sa_func.count(HotTopic.id))
        .filter(HotTopic.fetch_batch == latest_batch, HotTopic.platform == "zhihu")
        .group_by(HotTopic.source)
        .all()
    )

    sources = [SourceCount(source=source, count=count) for source, count in rows]
    total_topics = sum(item.count for item in sources)
    source_names = {item.source for item in sources}
    if not source_names:
        detected_source = "unknown"
    elif len(source_names) == 1:
        detected_source = next(iter(source_names))
    else:
        detected_source = "mixed"

    result = ZhihuSourceStatusResponse(
        mode=settings.HOT_ZHIHU_SOURCE_MODE,
        latest_batch=latest_batch,
        detected_source=detected_source,
        total_topics=total_topics,
        sources=sources,
    )
    cache_set(cache_key, result.model_dump(), CACHE_TTL_SECONDS)
    return result


@router.get("/grouped", response_model=GroupedHotResponse)
async def get_grouped_topics(
    platform: str = Query(None, description="Comma-separated platform filter"),
    db: Session = Depends(get_db),
):
    """Get hot topics grouped by keyword rules."""
    platforms = _parse_platforms(platform)
    cache_key = f"hot:grouped:{platform or 'all'}"

    cached = cache_get(cache_key)
    if cached is not None:
        return GroupedHotResponse(**cached)

    latest_batch = (
        db.query(HotTopic.fetch_batch)
        .filter(HotTopic.fetch_batch != "")
        .order_by(HotTopic.fetched_at.desc())
        .limit(1)
        .scalar()
    )

    if not latest_batch:
        return GroupedHotResponse(groups=[], unmatched=[], total=0)

    query = db.query(HotTopic).filter(HotTopic.fetch_batch == latest_batch)
    if platforms:
        query = query.filter(HotTopic.platform.in_(platforms))

    db_topics = query.order_by(HotTopic.hot_score.desc()).all()

    topic_dicts = [_enrich_platform_name(HotTopicResponse.model_validate(t).model_dump()) for t in db_topics]

    word_groups, filter_words, global_filters = get_keyword_rules()
    grouped, unmatched_list = group_topics_by_keywords(
        topic_dicts, word_groups, filter_words, global_filters,
    )

    groups = [
        KeywordGroupResponse(
            group_name=name,
            display_name=name,
            topics=[HotTopicResponse(**td) for td in topics],
            count=len(topics),
        )
        for name, topics in grouped.items()
    ]
    groups.sort(key=lambda g: g.count, reverse=True)

    unmatched_resp = [HotTopicResponse(**td) for td in unmatched_list]

    result = GroupedHotResponse(
        groups=groups,
        unmatched=unmatched_resp,
        total=len(db_topics),
    )
    cache_set(cache_key, result.model_dump(), CACHE_TTL_SECONDS)
    return result


@router.get("/history", response_model=HotHistoryResponse)
async def get_hot_history(
    days: int = Query(default=5, ge=1, le=5),
    platform: str = Query(None, description="Comma-separated platform filter"),
    db: Session = Depends(get_db),
):
    """Get hot topics history grouped by day, up to 5 days."""
    platforms = _parse_platforms(platform)
    cache_key = f"hot:history:{days}:{platform or 'all'}"

    cached = cache_get(cache_key)
    if cached is not None:
        return HotHistoryResponse(**cached)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        db.query(HotTopic)
        .filter(HotTopic.fetched_at >= cutoff, HotTopic.fetch_batch != "")
    )
    if platforms:
        query = query.filter(HotTopic.platform.in_(platforms))

    topics = query.order_by(HotTopic.fetched_at.desc()).all()

    batch_map: dict[str, list[HotTopic]] = defaultdict(list)
    for t in topics:
        batch_map[t.fetch_batch].append(t)

    day_map: dict[str, list[HotBatchResponse]] = defaultdict(list)
    for batch_id, batch_topics in sorted(batch_map.items(), reverse=True):
        if not batch_topics:
            continue
        date_str = batch_topics[0].fetched_at.strftime("%Y-%m-%d")
        items = [_topic_to_response(t) for t in batch_topics]
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
    return _topic_to_response(topic)
