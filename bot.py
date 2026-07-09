import logging
import time

from services.messengers.factory import build_adapters

from cache.client import get_redis
from cache.rate_limiter import RateLimiter
from cache.verse_cache import VerseCache
from config import Config
from scheduler import MessageScheduler
from services import user_service
from services.messengers.base import NormalizedMessage
from services.quran_api_client import QuranApiClient
from services.verse_ingestion_service import VerseIngestionService
from services.verse_service import VerseService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class BotRunner:
    """
    bot runner.
    The bot logic works with normalized messages.
    Telegram-API details are handled inside the adapter.
    """

    def __init__(
        self,
        verse_service: VerseService,
        rate_limiter: RateLimiter,
    ):
        self.adapters = build_adapters()
        self.verse_service = verse_service
        self.rate_limiter = rate_limiter

    def run_forever(self):
        api = self.adapters.get("PLATFORM")

        if not api:
            raise RuntimeError(
                "adapter is missing. Check BOT_TOKEN in .env"
            )

        logger.info("polling started")

        while True:
            try:
                messages = api.get_updates()

                if messages:
                    self._process_messages(
                        api,
                        messages,
                    )

                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Stopping bot...")
                raise

            except Exception as e:
                logger.error(f"main loop error: {e}")
                time.sleep(5)

    # -------------------------
    # Message processing
    # -------------------------

    def _process_messages(
        self,
        adapter,
        messages: list[NormalizedMessage],
    ):
        for message in messages:
            try:
                user_service.register_incoming_message(
                    message.platform,
                    {
                        "id": message.chat_id,
                        "type": message.chat_type,
                        "username": message.username,
                        "first_name": message.first_name,
                        "title": message.title,
                    },
                )

            except Exception as e:
                logger.error(
                    f"failed to register {message.platform}:{message.chat_id}: {e}"
                )

            text = message.text.strip()

            if text in ["/start", "شروع"]:
                self._handle_start(adapter, message)

            elif text in [
                "/random",
                "آیه تصادفی",
                "📖 ارسال آیه تصادفی",
            ]:
                self._handle_random(adapter, message)

            elif text in [
                "/help",
                "راهنما",
                "📚 راهنمای اضافه کردن به کانال",
            ]:
                self._handle_help(adapter, message)

            elif text in [
                "/schedule",
                "زمان",
            ]:
                self._handle_schedule(adapter, message)

            elif text == "/stats":
                self._handle_stats(adapter, message)

    # -------------------------
    # Command handlers
    # -------------------------

    def _handle_start(
        self,
        adapter,
        message: NormalizedMessage,
    ):
        text = (
            "🤖 *بازوی قرآن ناطق*\n\n"
            "سلام! خوش آمدید.\n\n"
            "📖 ارسال آیات تصادفی قرآن همراه با ترجمه.\n\n"
            "برای دریافت آیه تصادفی:\n"
            "/random"
        )

        adapter.send_message(
            message.chat_id,
            text,
        )

    def _handle_random(
        self,
        adapter,
        message: NormalizedMessage,
    ):
        rate_key = f"{message.platform}:{message.chat_id}"

        if not self.rate_limiter.allow(rate_key):
            wait = self.rate_limiter.remaining_seconds(rate_key)

            adapter.send_message(
                message.chat_id,
                f"⏳ لطفاً {wait} ثانیه دیگر دوباره تلاش کنید.",
            )

            return

        try:
            verse = self.verse_service.get_random_verse()

            if not verse:
                adapter.send_message(
                    message.chat_id,
                    "آیه‌ای پیدا نشد، بعداً دوباره امتحان کنید.",
                )
                return

            text = self.verse_service.format_verse(verse)

            adapter.send_message(
                message.chat_id,
                text,
                parse_mode="Markdown",
            )

            logger.info(f"sent verse -> {message.chat_id}")

        except Exception as e:
            logger.error(f"random verse error: {e}")

            adapter.send_message(
                message.chat_id,
                "خطایی رخ داد!",
            )

    def _handle_help(
        self,
        adapter,
        message: NormalizedMessage,
    ):
        text = (
            "📖 *راهنما*\n\n• /random → آیه تصادفی\n• /schedule → زمان ارسال خودکار\n"
        )

        adapter.send_message(
            message.chat_id,
            text,
        )

    def _handle_schedule(
        self,
        adapter,
        message: NormalizedMessage,
    ):
        text = (
            "⏰ *زمان ارسال*\n\n"
            f"📢 عمومی: "
            f"{Config.SCHEDULE_PUBLIC_HOUR:02d}:"
            f"{Config.SCHEDULE_PUBLIC_MINUTE:02d}\n"
            f"👤 کاربران: "
            f"{Config.SCHEDULE_USER_HOUR:02d}:"
            f"{Config.SCHEDULE_USER_MINUTE:02d}\n"
        )

        adapter.send_message(
            message.chat_id,
            text,
        )

    def _handle_stats(
        self,
        adapter,
        message: NormalizedMessage,
    ):
        if not user_service.is_admin(
            message.platform,
            message.chat_id,
        ):
            return

        stats = user_service.get_stats()

        last_ingestion = stats.get("last_verse_ingestion") or {}

        text = (
            "📊 *آمار*\n\n"
            f"👤 کاربران: {stats['users']}\n"
            f"👥 گروه‌ها: {stats['groups']}\n"
            f"📢 کانال‌ها: {stats['channels']}\n"
            f"🔄 آخرین بروزرسانی آیات: "
            f"{last_ingestion.get('count', '—')} "
            f"آیه در "
            f"{last_ingestion.get('at', 'نامشخص')}\n"
        )

        adapter.send_message(
            message.chat_id,
            text,
        )


# -------------------------
# MAIN ENTRY
# -------------------------


def main():
    print("=" * 60)
    print("🤖 Natiq Telegram Bot Starting")
    print("=" * 60)

    redis_client = get_redis()

    verse_cache = VerseCache(redis_client)

    verse_service = VerseService(verse_cache)

    rate_limiter = RateLimiter(
        redis_client,
        max_requests=Config.RATE_LIMIT_MAX_REQUESTS,
        window_seconds=Config.RATE_LIMIT_WINDOW_SECONDS,
    )

    api_client = QuranApiClient()

    ingestion_service = VerseIngestionService(
        api_client,
        verse_cache,
    )

    user_service.bootstrap_admins()
    user_service.seed_static_recipients()

    if Config.INGEST_ON_STARTUP:
        try:
            ingestion_service.ensure_data_available()

        except Exception as e:
            logger.error(f"Startup verse ingestion failed: {e}")

    runner = BotRunner(
        verse_service,
        rate_limiter,
    )

    if not runner.adapters:
        logger.error("No adapter configured. Check TELEGRAM_BOT_TOKEN in .env")
        return

    scheduler = MessageScheduler(
        runner.adapters,
        verse_service,
        ingestion_service,
    )

    scheduler.start()

    print("Bot is running on: " + ", ".join(runner.adapters.keys()))

    try:
        runner.run_forever()

    except KeyboardInterrupt:
        print("Stopping bot...")
        scheduler.stop()


if __name__ == "__main__":
    main()
