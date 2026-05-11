from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.models.user import User
from app.auth import get_current_user
from app.services.zhihu import zhihu_service

router = APIRouter(prefix="/api/publish", tags=["publish"])


class PublishRequest(BaseModel):
    content: str


class PublishResponse(BaseModel):
    success: bool
    message: str
    url: str = ""


@router.post("", response_model=PublishResponse)
async def publish_to_zhihu(
    req: PublishRequest,
    user: User = Depends(get_current_user),
):
    """Publish content to Zhihu circle as a pin."""
    if not user.zhihu_token:
        raise HTTPException(status_code=400, detail="No Zhihu token available. Please re-login.")

    try:
        result = await zhihu_service.publish_pin(user.zhihu_token, req.content)
        pin_url = result.get("url", result.get("pin_url", ""))
        return PublishResponse(success=True, message="发布成功", url=pin_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布失败: {e}")
