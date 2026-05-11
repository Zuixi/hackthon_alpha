from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HotTopicResponse(BaseModel):
    id: str
    question_id: Optional[str] = None
    title: str
    url: str
    excerpt: str
    hot_score: int
    answer_count: int
    follower_count: int
    detail: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class HotTopicListResponse(BaseModel):
    items: list[HotTopicResponse]
    total: int
