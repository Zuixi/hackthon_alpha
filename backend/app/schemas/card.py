from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateCardRequest(BaseModel):
    content: str
    tags: list[str] = []
    hot_topic_id: Optional[str] = None
    chat_session_id: Optional[str] = None


class UpdateCardRequest(BaseModel):
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class CardResponse(BaseModel):
    id: str
    content: str
    tags: list[str]
    hot_topic_id: Optional[str] = None
    hot_topic_title: Optional[str] = None
    chat_session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int
