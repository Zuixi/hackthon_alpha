from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    hot_topic_id: Optional[str] = None
    hot_topic_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    id: str
    title: str
    hot_topic_id: Optional[str] = None
    hot_topic_title: Optional[str] = None
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    hot_topic_id: Optional[str] = None
    message: str


class CreateSessionRequest(BaseModel):
    hot_topic_id: Optional[str] = None
    title: Optional[str] = None
