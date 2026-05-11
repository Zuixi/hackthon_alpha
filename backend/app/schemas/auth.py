from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    zhihu_id: str
    name: str
    avatar: str

    model_config = {"from_attributes": True}


class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None
