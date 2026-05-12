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
    total: int


class MomentListResponse(BaseModel):
    items: list[MomentResponse]
    total: int
