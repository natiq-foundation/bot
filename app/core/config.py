from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    APP_NAME: str = "Quran Bot"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------
    # Telegram
    # ------------------------------------------------------------------

    BOT_TOKEN: str
    BOT_USERNAME: str = ""

    BOT_API: str = "https://api.telegram.org"

    BOT_CONNECT_TIMEOUT: int = 20
    BOT_READ_TIMEOUT: int = 60
    BOT_WRITE_TIMEOUT: int = 60
    BOT_POOL_TIMEOUT: int = 30

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    DATABASE_URL: str

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------

    REDIS_URL: str

    # ------------------------------------------------------------------
    # Natiq API
    # ------------------------------------------------------------------

    NATIQ_PRIMARY_API: str = Field(
        default="https://api.natiq.net/api"
    )

    NATIQ_SECONDARY_API: str = Field(
        default="https://api.natiq.ir/api"
    )

    NATIQ_API_TOKEN: str = ""

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    CACHE_DEFAULT_TTL: int = 3600

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------

    DEFAULT_TIMEZONE: str = "Asia/Tehran"

    # ------------------------------------------------------------------
    # Features
    # ------------------------------------------------------------------

    ENABLE_SEARCH: bool = True
    ENABLE_FAVORITES: bool = True
    ENABLE_DAILY_AYAH: bool = True
    ENABLE_ADMIN: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
