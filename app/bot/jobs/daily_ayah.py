from __future__ import annotations

import logging
from datetime import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes, JobQueue

from app.bot.services.delivery import (
    DeliveryTarget,
    deliver_ayah,
    deliver_page,
    inline_keyboards_supported,
)
from app.bot.services.quran import QuranService
from app.core.config import resolve_timezone
from app.i18n import detect_language

if TYPE_CHECKING:
    from app.database.models.chat import Chat

logger = logging.getLogger(__name__)


def _resolve_timezone(chat: "Chat") -> ZoneInfo:
    return resolve_timezone(chat.timezone)


def _parse_daily_time(chat: "Chat") -> time | None:
    try:
        hour_str, minute_str = chat.daily_time.split(":", 1)
        return time(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, AttributeError):
        logger.warning(
            "Invalid daily_time for chat_id=%s: %r",
            chat.chat_id,
            chat.daily_time,
        )
        return None


def _daily_ayah_job_name(chat_id: int) -> str:
    return f"daily_ayah_{chat_id}"


async def send_daily_ayah_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send the daily ayah to the single user this job was scheduled for.

    Each user gets their own deterministic daily job (see ``schedule_user_daily_ayah``),
    which fires at their exact local time. The ``last_daily_sent_date`` field guards
    against accidental duplicates.
    """
    job = context.job
    if job is None or not isinstance(job.data, dict):
        logger.warning("Daily ayah job invoked without chat_id data")
        return

    chat_id = job.data.get("chat_id")
    if chat_id is None:
        logger.warning("Daily ayah job missing chat_id")
        return

    try:
        from app.database.repositories.chat import ChatRepository

        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

        if not chat_repo:
            logger.warning("Chat repository is not available")
            return

        user = await chat_repo.get_by_telegram_id(chat_id)

        if user is None:
            logger.info(
                "User no longer exists, removing daily ayah job: chat_id=%s", chat_id
            )
            remove_daily_ayah_job(context.application, chat_id)
            return

        # Check if user has daily ayah enabled
        if not user.daily_ayah:
            logger.debug(
                "Daily ayah disabled for user: telegram_id=%s",
                user.chat_id,
            )
            return

        # Check if already sent today
        if not await chat_repo.should_send_daily_ayah(user.chat_id):
            logger.debug(
                "Already sent today: telegram_id=%s",
                user.chat_id,
            )
            return

        service = QuranService.from_application(context.application)
        language = detect_language(user.language)
        target = DeliveryTarget.for_chat(
            context.bot,
            user.chat_id,
            language,
            inline_keyboards=inline_keyboards_supported(context.application),
        )

        if user.daily_type == "page":
            ayahs = await service.pick_page(
                delivery_mode=user.delivery_mode,
                chat_uuid=user.uuid,
            )
            await service.record_page(user.chat_id, ayahs)
            await deliver_page(
                target,
                ayahs,
                show_translation=False,
                include_settings=True,
            )
        else:
            ayah = await service.pick_ayah(
                delivery_mode=user.delivery_mode,
                chat_uuid=user.uuid,
            )
            await service.record_ayah(user.chat_id, ayah)
            await deliver_ayah(
                target,
                ayah,
                include_settings=True,
            )

        # Mark as sent
        await chat_repo.mark_daily_ayah_sent(user.chat_id)

        logger.info(
            "Sent daily %s: telegram_id=%s, delivery_mode=%s",
            user.daily_type,
            user.chat_id,
            user.delivery_mode,
        )

    except Exception as exc:
        logger.exception(
            "Failed to send daily ayah: telegram_id=%s, error=%s",
            chat_id,
            exc,
        )


def remove_daily_ayah_job(application: Application, chat_id: int) -> None:
    """Cancel any scheduled daily ayah job for the given chat."""
    job_queue: JobQueue | None = application.job_queue
    if job_queue is None:
        return

    name = _daily_ayah_job_name(chat_id)
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()


def schedule_user_daily_ayah(
    application: Application,
    chat: "Chat",
    *,
    replace_existing: bool = True,
) -> None:
    """
    Schedule a deterministic daily ayah job for a single user.

    The job runs at the user's local time (``chat.daily_time`` in ``chat.timezone``)
    and repeats every day. Any previously scheduled job for the same chat is replaced
    unless ``replace_existing`` is False (used at startup, when no jobs exist yet,
    to avoid an O(n^2) scan of the job queue).
    """
    job_queue: JobQueue | None = application.job_queue
    if job_queue is None:
        return

    if replace_existing:
        remove_daily_ayah_job(application, chat.chat_id)

    if not chat.daily_ayah:
        logger.info("Daily ayah disabled, removing job: chat_id=%s", chat.chat_id)
        return

    tz = _resolve_timezone(chat)
    due_time = _parse_daily_time(chat)
    if due_time is None:
        return

    due_time = due_time.replace(tzinfo=tz)

    job_queue.run_daily(
        send_daily_ayah_job,
        time=due_time,
        days=tuple(range(7)),  # Every day
        name=_daily_ayah_job_name(chat.chat_id),
        data={"chat_id": chat.chat_id},
    )

    logger.info(
        "Scheduled daily ayah: chat_id=%s, time=%s, tz=%s",
        chat.chat_id,
        due_time.strftime("%H:%M"),
        tz.key,
    )


async def schedule_daily_ayah(application: Application) -> None:
    """
    Schedule deterministic daily ayah jobs for all users with daily ayah enabled.

    Called once at startup. Individual users are (re)scheduled as their preferences
    change via ``schedule_user_daily_ayah``.
    """
    container = application.bot_data.get("container")
    chat_repo = application.bot_data.get("user_repository")

    if not container or not chat_repo:
        logger.warning("Container or chat repository not available")
        return

    chats = await chat_repo.list_daily_ayah_enabled()

    for chat in chats:
        schedule_user_daily_ayah(application, chat, replace_existing=False)

    logger.info("Scheduled daily ayah for %d users", len(chats))
