from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HotTopicResponse(BaseModel):
    id: str
    question_id: Optional[str] = None
    title: str
    url: str
    thumbnail_url: str = ""
    excerpt: str
    hot_score: int
    answer_count: int
    follower_count: int
    detail: str
    fetch_batch: str = ""
    fetched_at: datetime

    model_config = {"from_attributes": True}


class HotTopicListResponse(BaseModel):
    items: list[HotTopicResponse]
    total: int


class HotBatchResponse(BaseModel):
    """A single fetch batch with its topics."""
    fetch_batch: str
    fetched_at: datetime
    items: list[HotTopicResponse]
    count: int


class HotDayGroup(BaseModel):
    """One day's worth of hot topic batches."""
    date: str
    batches: list[HotBatchResponse]
    topic_count: int


class HotHistoryResponse(BaseModel):
    """History of hot topics grouped by day."""
    days: list[HotDayGroup]
    total_days: int
