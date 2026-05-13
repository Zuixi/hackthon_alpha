from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional


class FolloweeResponse(BaseModel):
    uid: int | str
    hash_id: str = ""
    fullname: str = ""
    gender: str = ""
    headline: str = ""
    description: str = ""
    avatar_path: str = ""
    url: str = ""


class SocialPageMeta(BaseModel):
    page: int
    per_page: int
    items_count: int
    has_more: bool
    is_end: bool
    next_page: Optional[int] = None
    total: Optional[int] = None


class MomentAuthor(BaseModel):
    name: str = ""


class MomentTarget(BaseModel):
    title: str = ""
    excerpt: str = ""
    author: Optional[MomentAuthor] = None


class MomentActor(BaseModel):
    name: str = ""


class MomentResponse(BaseModel):
    actor: MomentActor
    action_text: str = ""
    action_time: int = 0
    target: Optional[MomentTarget] = None


class FolloweeListResponse(BaseModel):
    items: list[FolloweeResponse]
    page: SocialPageMeta


class MomentListResponse(BaseModel):
    items: list[MomentResponse]
    total: int


class FollowerSnapshotItem(BaseModel):
    snapshot_date: date
    follower_count: int
    delta: Optional[int] = None
    refreshed_at: datetime


class FollowerStatsResponse(BaseModel):
    items: list[FollowerSnapshotItem]
    total_days: int
    latest_count: Optional[int] = None
    next_refresh_at: str = "每天 20:00 (Asia/Shanghai)"
