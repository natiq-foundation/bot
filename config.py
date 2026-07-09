import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


class Config:
    # =====================================================
    # Telegram
    # =====================================================

    BOT_TOKEN: str = os.getenv(
        "BOT_TOKEN",
        "",
    )

    API_URL: str = os.getenv(
        "API_URL",
        "",
    )
    PLATFORM_NAME = os.getenv(
    "PLATFORM_NAME",
    "telegram",
    )

    PLATFORM_API = os.getenv(
    "PLATFORM_API",
    "https://api.telegram.org",
    )

    # =====================================================
    # Debug
    # =====================================================

    DEBUG: bool = (
        os.getenv(
            "DEBUG",
            "False",
        ).lower()
        == "true"
    )

    DEBUG_VERSE_LIMIT: int = int(
        os.getenv(
            "DEBUG_VERSE_LIMIT",
            "200",
        )
    )

    # =====================================================
    # Quran API
    # =====================================================

    QURAN_API_URL: str = os.getenv(
        "QURAN_API_URL",
        "https://api.natiq.ir/api",
    )

    MUSHAF: str = os.getenv(
        "MUSHAF",
        "hafs",
    )

    TRANSLATOR_UUID: str = os.getenv(
        "TRANSLATOR_UUID",
        "",
    )

    PAGE_SIZE: int = int(
        os.getenv(
            "PAGE_SIZE",
            "200",
        )
    )

    # =====================================================
    # Scheduler
    # =====================================================

    SCHEDULE_PUBLIC_HOUR: int = int(
        os.getenv(
            "SCHEDULE_PUBLIC_HOUR",
            "12",
        )
    )

    SCHEDULE_PUBLIC_MINUTE: int = int(
        os.getenv(
            "SCHEDULE_PUBLIC_MINUTE",
            "0",
        )
    )

    SCHEDULE_USER_HOUR: int = int(
        os.getenv(
            "SCHEDULE_USER_HOUR",
            "3",
        )
    )

    SCHEDULE_USER_MINUTE: int = int(
        os.getenv(
            "SCHEDULE_USER_MINUTE",
            "0",
        )
    )

    SCHEDULE_TIMEZONE: str = os.getenv(
        "SCHEDULE_TIMEZONE",
        "Asia/Riyadh",
    )

    # Refresh Quran data interval

    VERSE_REFRESH_INTERVAL_HOURS: int = int(
        os.getenv(
            "VERSE_REFRESH_INTERVAL_HOURS",
            "24",
        )
    )

    INGEST_ON_STARTUP: bool = (
        os.getenv(
            "INGEST_ON_STARTUP",
            "True",
        ).lower()
        == "true"
    )

    # =====================================================
    # Static recipients
    # =====================================================

    @staticmethod
    def _parse_ids(
        env_var: str,
    ) -> List[str]:
        value = os.getenv(
            env_var,
            "",
        )

        if not value:
            return []

        return [item.strip() for item in value.split(",") if item.strip()]

    @classmethod
    def get_seed_channel_ids(cls) -> List[str]:
        return cls._parse_ids("CHANNEL_IDS")

    @classmethod
    def get_seed_group_ids(cls) -> List[str]:
        return cls._parse_ids("GROUP_IDS")

    @classmethod
    def get_seed_user_ids(cls) -> List[str]:
        return cls._parse_ids("USER_IDS")

    @classmethod
    def get_admin_ids(cls) -> List[str]:
        return cls._parse_ids("ADMIN_USER_IDS")

    # =====================================================
    # Rate limiting
    # =====================================================

    RATE_LIMIT_MAX_REQUESTS: int = int(
        os.getenv(
            "RATE_LIMIT_MAX_REQUESTS",
            "5",
        )
    )

    RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.getenv(
            "RATE_LIMIT_WINDOW_SECONDS",
            "60",
        )
    )

    # =====================================================
    # Database
    # =====================================================

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "",
    )

    # =====================================================
    # Redis
    # =====================================================

    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )
