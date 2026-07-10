from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    PERSIAN = "fa"
    ARABIC = "ar"
    TURKISH = "tr"


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class ParseMode(str, Enum):
    HTML = "HTML"
    MARKDOWN = "MarkdownV2"


class UserState(str, Enum):
    NONE = "none"

    SEARCH = "search"

    SETTINGS = "settings"

    SELECT_TRANSLATION = "select_translation"

    SELECT_RECITER = "select_reciter"


class CachePrefix(str, Enum):
    USER = "user"

    CHAT = "chat"

    AYAH = "ayah"

    SURAH = "surah"

    TRANSLATION = "translation"

    RECITATION = "recitation"

    SETTINGS = "settings"

    STATE = "state"

    DAILY = "daily"
