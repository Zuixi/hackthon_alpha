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
    REDIS_URL: str = "redis://localhost:6379/0"

    # MiniMax
    MINIMAX_API_KEY: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2.7"

    # Zhihu OAuth  (base = openapi.zhihu.com per official docs)
    ZHIHU_APP_ID: str = ""
    ZHIHU_APP_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    ZHIHU_REDIRECT_URI: str = "http://localhost:5173/auth/callback"
    ZHIHU_OAUTH_BASE_URL: str = "https://openapi.zhihu.com"

    # Zhihu Developer API  (developer.zhihu.com)
    ZHIHU_ACCESS_SECRET: str = ""
    ZHIHU_DEV_BASE_URL: str = "https://developer.zhihu.com"

    @property
    def ZHIHU_DEV_TOKEN(self) -> str:
        """Unified developer bearer token."""
        return self.ZHIHU_ACCESS_SECRET

    # Zhihu Community / Circle API  (openapi under zhihu.com)
    ZHIHU_COMMUNITY_BASE_URL: str = "https://openapi.zhihu.com"

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    # Development
    BYPASS_OAUTH_LOGIN: bool = False

    model_config = {"env_file": str(_env_file), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
