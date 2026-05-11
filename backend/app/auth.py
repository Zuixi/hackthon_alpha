from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def normalize_redirect_uri(redirect_uri: str = "") -> str:
    """
    Normalize OAuth redirect URI to avoid common config mistakes:
    - trim whitespace
    - fill default from settings when empty
    - append /auth/callback when only origin is provided
    """
    raw = (redirect_uri or settings.ZHIHU_REDIRECT_URI or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect_uri")

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect_uri")

    path = parsed.path or ""
    if path in ("", "/"):
        path = "/auth/callback"

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if settings.BYPASS_OAUTH_LOGIN:
        user = db.query(User).filter(User.zhihu_id == "dev-bypass-user").first()
        if not user:
            user = User(
                zhihu_id="dev-bypass-user",
                name="本地调试用户",
                avatar="",
                zhihu_token="",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
