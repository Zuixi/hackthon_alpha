import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.hot_topic import HotTopic
from app.schemas.hot import HotTopicResponse, HotTopicListResponse
from app.services.zhihu import zhihu_service
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/api/hot", tags=["hot"])
logger = logging.getLogger(__name__)

CACHE_KEY = "hot:topics"
CACHE_TTL_SECONDS = 3600


@router.get("", response_model=HotTopicListResponse)
async def get_hot_topics(limit: int = 50, db: Session = Depends(get_db)):
    """Get hot topics with Redis caching and DB fallback."""
    cached = cache_get(CACHE_KEY)
    if cached is not None:
        items = cached[:limit]
        return HotTopicListResponse(items=items, total=len(items))

    try:
        raw = await zhihu_service.get_hot_list(hours=24, limit=limit)
        topics_data = raw.get("data", raw.get("items", []))
        if isinstance(raw, list):
            topics_data = raw

        now = datetime.now(timezone.utc)
        db_topics = []

        for item in topics_data:
            qid = str(item.get("question_id", item.get("id", "")))
            topic = HotTopic(
                question_id=qid,
                title=item.get("title", item.get("question", {}).get("title", "")),
                url=item.get("url", item.get("question", {}).get("url", "")),
                excerpt=item.get("excerpt", item.get("answer", {}).get("excerpt", "")),
                hot_score=int(item.get("hot_score", item.get("score", 0))),
                answer_count=int(item.get("answer_count", 0)),
                follower_count=int(item.get("follower_count", 0)),
                detail=str(item.get("detail", "")),
                fetched_at=now,
            )
            db.add(topic)
            db_topics.append(topic)

        db.commit()
        for t in db_topics:
            db.refresh(t)

        result = [HotTopicResponse.model_validate(t).model_dump() for t in db_topics]
        cache_set(CACHE_KEY, result, CACHE_TTL_SECONDS)

        return HotTopicListResponse(
            items=[HotTopicResponse(**r) for r in result[:limit]],
            total=len(result),
        )

    except Exception as e:
        logger.warning("Failed to fetch from Zhihu API: %s, falling back to DB", e)
        db_topics = (
            db.query(HotTopic)
            .order_by(HotTopic.fetched_at.desc(), HotTopic.hot_score.desc())
            .limit(limit)
            .all()
        )
        result = [HotTopicResponse.model_validate(t) for t in db_topics]
        return HotTopicListResponse(items=result, total=len(result))


@router.get("/{topic_id}", response_model=HotTopicResponse)
async def get_hot_topic(topic_id: str, db: Session = Depends(get_db)):
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic
