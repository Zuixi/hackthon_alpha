from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent

_env_candidates = [
    _root_dir / ".env",       # project root (preferred)
    _backend_dir / ".env",    # backend dir
]
_env_file = next((p for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://creator:password@localhost:5432/creator_assistant"

    # MiniMax
    MINIMAX_API_KEY: str = ""
    MINIMAX_MODEL: str = "MiniMax-M1"

    # Zhihu OAuth  (base = openapi.zhihu.com per official docs)
    ZHIHU_APP_ID: str = ""
    ZHIHU_APP_KEY: str = ""
    ZHIHU_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    ZHIHU_OAUTH_BASE_URL: str = "https://openapi.zhihu.com"

    # Zhihu Developer API  (developer.zhihu.com)
    ZHIHU_DEV_API_KEY: str = ""
    ZHIHU_DEV_BASE_URL: str = "https://api.zhihu.com"

    # Zhihu Community / Circle API  (openapi under zhihu.com)
    ZHIHU_COMMUNITY_BASE_URL: str = "https://openapi.zhihu.com"

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    model_config = {"env_file": str(_env_file), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
