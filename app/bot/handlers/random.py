from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables:
    - BOT_TOKEN: Telegram bot token (required)
    - DATABASE_URL: PostgreSQL connection URL
    - REDIS_URL: Redis connection URL
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    - QURAN_MUSHAF: Quran script (default: hafs)
    - QURAN_TRANSLATION_LANGUAGE: Translation language (default: fa)
    - NATIQ_API_TIMEOUT: API timeout in seconds (default: 120)
    """

    # Application
    APP_NAME: str = "Quran Bot"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Bot
    BOT_TOKEN: str = ""
    BOT_USERNAME: str = "@NatiqChatBot"
    BOT_API: str = "https://api.telegram.org"
    PLATFORM: str = "TELEGRAM"
    BOT_LANGUAGE: str = "fa"
    ADMIN_USER_IDS: str = ""  # Comma-separated list

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/quran_bot"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure DATABASE_URL is not empty."""
        if not v or not v.strip():
            raise ValueError("DATABASE_URL must be set")
        return v.strip()

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Natiq API
    NATIQ_API_URL: str = "https://api.natiq.net/"
    NATIQ_PRIMARY_API: str = "https://api.natiq.net/"
    NATIQ_SECONDARY_API: str | None = None
    NATIQ_API_TOKEN: str | None = None
    NATIQ_API_TIMEOUT: int = 120

    # Quran
    QURAN_MUSHAF: str = "hafs"
    QURAN_TRANSLATION_LANGUAGE: str = "fa"
    QURAN_TRANSLATOR: str | None = None

    # Daily Ayah Settings
    # Hardcoded base: UTC (Greenwich) at 00:00
    # Environment override: Set to Asia/Riyadh at 03:15 in .env
    DAILY_AYAH_DEFAULT_TIME: str = "03:15"  # Default time in configured timezone
    DAILY_AYAH_DEFAULT_TIMEZONE: str = "Asia/Riyadh"  # Default timezone for users

    # Cache
    CACHE_ENABLED: bool = True

    # Timezone
    TZ: str = "UTC"

    @field_validator("NATIQ_API_TIMEOUT", mode="before")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate API timeout is positive."""
        if not isinstance(v, int):
            v = int(v)

        if v <= 0:
            raise ValueError("NATIQ_API_TIMEOUT must be greater than zero")

        return v

    @field_validator("NATIQ_PRIMARY_API", mode="before")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API URL is not empty."""
        if not v or not v.strip():
            raise ValueError("NATIQ_PRIMARY_API must not be empty")

        return v.strip()

    @property
    def admin_user_ids(self) -> set[int]:
        """
        Parse comma-separated admin user IDs.

        Returns:
            Set of admin user IDs
        """
        values: set[int] = set()

        if not self.ADMIN_USER_IDS:
            return values

        for raw_item in self.ADMIN_USER_IDS.split(","):
            item = raw_item.strip()

            if not item:
                continue

            try:
                values.add(int(item))
            except ValueError:
                continue

        return values

    @property
    def api_headers(self) -> dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary with Accept and optional Authorization headers
        """
        headers = {"Accept": "application/json"}

        if self.NATIQ_API_TOKEN:
            headers["Authorization"] = f"Bearer {self.NATIQ_API_TOKEN}"

        return headers

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local", ".env.docker"],
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings object
    """
    return Settings()


def resolve_timezone(timezone_name: str | None) -> ZoneInfo:
    """
    Resolve a timezone name to a ZoneInfo, falling back to the configured
    default timezone and finally UTC when the name is missing or invalid.
    """
    settings = get_settings()
    try:
        return ZoneInfo(timezone_name or settings.DAILY_AYAH_DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo("UTC")


def validate_runtime_settings() -> Settings:
    """
    Validate runtime settings at startup.

    Returns:
        Settings object

    Raises:
        ValueError: If BOT_TOKEN is missing
    """
    settings = get_settings()

    if not settings.BOT_TOKEN or not settings.BOT_TOKEN.strip():
        raise ValueError(
            "BOT_TOKEN environment variable must be set. "
            "Get it from @BotFather on Telegram."
        )

    return settings
