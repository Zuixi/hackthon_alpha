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
    platform: str = "zhihu"
    platform_name: str = "知乎"
    source: str = "zhihu_api"
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


class PlatformInfo(BaseModel):
    id: str
    name: str
    count: int

class PlatformListResponse(BaseModel):
    platforms: list[PlatformInfo]


class KeywordGroupResponse(BaseModel):
    group_name: str
    display_name: str
    topics: list[HotTopicResponse]
    count: int

class GroupedHotResponse(BaseModel):
    groups: list[KeywordGroupResponse]
    unmatched: list[HotTopicResponse]
    total: int


class SourceCount(BaseModel):
    source: str
    count: int


class ZhihuSourceStatusResponse(BaseModel):
    mode: str
    latest_batch: str
    detected_source: str
    total_topics: int
    sources: list[SourceCount]
