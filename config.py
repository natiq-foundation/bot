import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot
    BALE_BOT_TOKEN: str = os.getenv("BALE_BOT_TOKEN", "")
    BALE_API_URL: str = os.getenv("BALE_API_URL", "https://tapi.bale.ai")
    
    # Quran API
    QURAN_API_URL: str = os.getenv("QURAN_API_URL", "http://localhost")
    MUSHAF: str = os.getenv("MUSHAF", "hafs")
    TRANSLATOR_UUID: str = os.getenv("TRANSLATOR_UUID", "")
    PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "-1"))
    
    # Scheduler
    SCHEDULE_HOUR: int = int(os.getenv("SCHEDULE_HOUR", "3"))
    SCHEDULE_MINUTE: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    SCHEDULE_TIMEZONE: str = os.getenv("SCHEDULE_TIMEZONE", "Asia/Riyadh")
    
    # Recipients
    @staticmethod
    def _parse_ids(env_var: str) -> List[int]:
        value = os.getenv(env_var, "")
        if not value:
            return []
        return [int(id_str.strip()) for id_str in value.split(",") if id_str.strip()]
    
    @classmethod
    def get_channel_ids(cls) -> List[int]:
        return cls._parse_ids("CHANNEL_IDS")
    
    @classmethod
    def get_group_ids(cls) -> List[int]:
        return cls._parse_ids("GROUP_IDS")
    
    @classmethod
    def get_user_ids(cls) -> List[int]:
        return cls._parse_ids("USER_IDS")
    
    @classmethod
    def get_all_recipients(cls) -> List[int]:
        return (
            cls.get_channel_ids() +
            cls.get_group_ids() +
            cls.get_user_ids()
        )
    
    # Computed Properties
    @classmethod
    def get_bale_full_api_url(cls) -> str:
        return f"{cls.BALE_API_URL}/bot{cls.BALE_BOT_TOKEN}"
