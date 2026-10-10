from app.bot.handlers.random import format_ayah
from app.core.config import get_settings
from app.schemas.ayah import Ayah


def build_ayah(
    *,
    surah_icon: str,
    surah_period: str,
    text: str = "sample text",
    ayah_number: int = 7,
    bismillah_text: str | None = None,
    bismillah_is_ayah: bool = False,
    show_bismillah_line: bool = False,
) -> Ayah:
    return Ayah(
        uuid="ayah-1",
        text=text,
        translation="sample translation",
        surah_uuid="surah-1",
        surah_name="الفاتحة",
        surah_number=1,
        surah_period=surah_period,
        surah_icon=surah_icon,
        bismillah_text=bismillah_text,
        bismillah_is_ayah=bismillah_is_ayah,
        show_bismillah_line=show_bismillah_line,
        ayah_number=ayah_number,
        page=1,
        juz=1,
    )


def test_format_ayah_includes_makki_icon() -> None:
    ayah = build_ayah(
        surah_icon="🕋",
        surah_period="makki",
    )

    text = format_ayah(ayah)
    settings = get_settings()

    assert "🕋 الفاتحة" in text
    assert "📖 sample text ﴿7﴾" in text
    assert "📝 sample translation" in text
    assert "(7)" not in text
    assert settings.BOT_USERNAME in text


def test_format_ayah_includes_madani_icon() -> None:
    ayah = build_ayah(
        surah_icon="🕌",
        surah_period="madani",
    )

    text = format_ayah(ayah)

    assert "🕌 الفاتحة" in text


def test_format_ayah_omits_extra_space_without_icon() -> None:
    ayah = build_ayah(
        surah_icon="",
        surah_period="unknown",
    )

    text = format_ayah(ayah)

    assert "الفاتحة" in text
    assert "\n\n📖 sample text ﴿7﴾" in text
    assert "📝 sample translation" in text
    assert " الفاتحة" not in text


def test_format_ayah_shows_bismillah_line_for_first_non_bismillah_ayah() -> None:
    bismillah_text = "fixture bismillah"
    ayah_text = "الْحَمْدُ لِلَّهِ"
    ayah = build_ayah(
        surah_icon="🕌",
        surah_period="madani",
        text=ayah_text,
        ayah_number=1,
        bismillah_text=bismillah_text,
        bismillah_is_ayah=False,
        show_bismillah_line=True,
    )

    text = format_ayah(ayah)

    expected_prefix = f"{bismillah_text}\n\n📖 {ayah_text} ﴿1﴾"
    assert expected_prefix in text


def test_format_ayah_does_not_show_bismillah_line_when_surah_has_no_bismillah() -> None:
    ayah_text = "sample first ayah"
    ayah = build_ayah(
        surah_icon="🕌",
        surah_period="madani",
        text=ayah_text,
        ayah_number=1,
        bismillah_text=None,
        bismillah_is_ayah=False,
        show_bismillah_line=False,
    )

    text = format_ayah(ayah)

    assert f"📖 {ayah_text} ﴿1﴾" in text
    assert "fixture bismillah" not in text
