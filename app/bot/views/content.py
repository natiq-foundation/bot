from __future__ import annotations

from app.core.config import get_settings
from app.schemas.ayah import Ayah


def footer() -> str:
    """Return the standard bot attribution line."""
    return f"📱 {get_settings().BOT_USERNAME}"


def with_footer(text: str) -> str:
    """Append the standard bot attribution to a user-facing message."""
    return f"{text}\n\n{footer()}"


def _surah_header(ayah: Ayah) -> str:
    if ayah.surah_icon:
        return f"{ayah.surah_icon} {ayah.surah_name}"
    return ayah.surah_name


def format_ayah(ayah: Ayah) -> str:
    """Format a single ayah with readable spacing."""
    parts: list[str] = [_surah_header(ayah)]

    if ayah.show_bismillah_line and ayah.bismillah_text:
        parts.append(ayah.bismillah_text)

    parts.append(f"📖 {ayah.text} ﴿{ayah.ayah_number}﴾")

    if ayah.translation:
        parts.append(f"📝 {ayah.translation}")

    parts.append(footer())

    return "\n\n".join(parts)


def format_page(
    ayahs: list[Ayah],
    *,
    show_translation: bool = False,
) -> str:
    """Format a page (group of ayahs), supporting multi-surah transitions."""
    if not ayahs:
        return footer()

    parts: list[str] = []
    current_surah_uuid: str | None = None
    page_number = ayahs[0].page or "?"

    for ayah in ayahs:
        # A page can span more than one surah, so print a fresh header each
        # time the surah changes and repeat the bismillah when appropriate.
        if ayah.surah_uuid != current_surah_uuid:
            current_surah_uuid = ayah.surah_uuid

            if parts:
                parts.append("")

            icon = ayah.surah_icon or "🕋"
            parts.append(f"{icon} {ayah.surah_name} (Page {page_number})")

            if ayah.show_bismillah_line and ayah.bismillah_text:
                parts.append(ayah.bismillah_text)

            parts.append("")

        parts.append(f"📖 {ayah.text} ﴿{ayah.ayah_number}﴾")

        if show_translation and ayah.translation:
            parts.append(f"📝 {ayah.translation}")
            parts.append("")

    parts.append("")
    parts.append(footer())

    return "\n".join(parts).strip()
