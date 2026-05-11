import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.hot_topic import HotTopic
from app.schemas.hot import HotTopicResponse, HotTopicListResponse
from app.services.zhihu import zhihu_service

router = APIRouter(prefix="/api/hot", tags=["hot"])
logger = logging.getLogger(__name__)

_cache: dict = {"data": None, "fetched_at": None}
CACHE_TTL_SECONDS = 3600


def _is_cache_valid() -> bool:
    if _cache["data"] is None or _cache["fetched_at"] is None:
        return False
    age = (datetime.now(timezone.utc) - _cache["fetched_at"]).total_seconds()
    return age < CACHE_TTL_SECONDS


@router.get("", response_model=HotTopicListResponse)
async def get_hot_topics(limit: int = 50, db: Session = Depends(get_db)):
    """Get hot topics, using cache to respect API rate limits."""
    if _is_cache_valid():
        items = _cache["data"][:limit]
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

        result = [HotTopicResponse.model_validate(t) for t in db_topics]
        _cache["data"] = result
        _cache["fetched_at"] = now

        return HotTopicListResponse(items=result[:limit], total=len(result))

    except Exception as e:
        logger.warning(f"Failed to fetch from Zhihu API: {e}, falling back to DB cache")
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
