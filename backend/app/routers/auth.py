from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.auth import create_access_token, get_current_user, normalize_redirect_uri
from app.schemas.auth import TokenResponse, UserResponse, OAuthCallbackRequest
from app.services.zhihu import zhihu_service
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login-url")
async def get_login_url(redirect_uri: str = ""):
    """Return the Zhihu OAuth authorization URL per official docs:
    https://openapi.zhihu.com/authorize?redirect_uri=...&app_id=...&response_type=code
    """
    uri = normalize_redirect_uri(redirect_uri)
    query = urlencode(
        {"app_id": settings.ZHIHU_APP_ID, "redirect_uri": uri, "response_type": "code"}
    )
    url = f"{settings.ZHIHU_OAUTH_BASE_URL}/authorize?{query}"
    return {"url": url}


@router.post("/callback", response_model=TokenResponse)
async def oauth_callback(req: OAuthCallbackRequest, db: Session = Depends(get_db)):
    """Exchange Zhihu OAuth code for JWT token."""
    redirect_uri = normalize_redirect_uri(req.redirect_uri)
    try:
        token_data = await zhihu_service.exchange_oauth_token(req.code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")

    user_token = token_data.get("access_token") or token_data.get("token", "")
    zhihu_uid = str(token_data.get("uid", "") or token_data.get("user_id", ""))

    if not zhihu_uid:
        try:
            user_info = await zhihu_service.get_user_info(user_token)
            zhihu_uid = str(user_info.get("uid", user_info.get("id", "")))
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to get user info")

    user_name = token_data.get("fullname", token_data.get("name", "知乎用户"))
    user_avatar = token_data.get("avatar_path", token_data.get("avatar_url", ""))

    if not user_name or user_name == "知乎用户":
        try:
            info = await zhihu_service.get_user_info(user_token)
            user_name = info.get("fullname", info.get("name", user_name))
            user_avatar = info.get("avatar_path", info.get("avatar_url", user_avatar))
        except Exception:
            pass

    user = db.query(User).filter(User.zhihu_id == zhihu_uid).first()

    if user:
        user.name = user_name
        user.avatar = user_avatar
        user.zhihu_token = user_token
    else:
        user = User(
            zhihu_id=zhihu_uid,
            name=user_name,
            avatar=user_avatar,
            zhihu_token=user_token,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    jwt_token = create_access_token(user.id)
    return TokenResponse(access_token=jwt_token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
