from enum import Enum


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class ContentMode(str, Enum):
    RANDOM_AYAH = "random_ayah"
    RANDOM_PAGE = "random_page"
    SPECIFIC_AYAH = "specific_ayah"
    SPECIFIC_PAGE = "specific_page"


# Timezone data organized by continent, shared by the user settings wizard and
# the group-admin settings panel.
TIMEZONE_CONTINENTS: dict[str, list[str]] = {
    "Africa": [
        "Africa/Cairo",
        "Africa/Casablanca",
        "Africa/Johannesburg",
        "Africa/Lagos",
        "Africa/Nairobi",
    ],
    "Asia": [
        "Asia/Dubai",
        "Asia/Riyadh",
        "Asia/Tehran",
        "Asia/Karachi",
        "Asia/Dhaka",
        "Asia/Jakarta",
        "Asia/Kolkata",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Asia/Bangkok",
        "Asia/Singapore",
        "Asia/Hong_Kong",
        "Asia/Shanghai",
    ],
    "Europe": [
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Rome",
        "Europe/Madrid",
        "Europe/Moscow",
        "Europe/Istanbul",
        "Europe/Amsterdam",
        "Europe/Brussels",
        "Europe/Vienna",
    ],
    "America": [
        "America/New_York",
        "America/Los_Angeles",
        "America/Chicago",
        "America/Mexico_City",
        "America/Toronto",
        "America/Bogota",
        "America/Lima",
        "America/Santiago",
        "America/Buenos_Aires",
        "America/Sao_Paulo",
    ],
    "Australia": [
        "Australia/Sydney",
        "Australia/Melbourne",
        "Australia/Brisbane",
        "Australia/Perth",
        "Australia/Adelaide",
    ],
}
