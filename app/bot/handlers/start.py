from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        (
            "السلام عليكم\n\n"
            "Welcome to Natiq Quran Bot.\n\n"
            "The project is running successfully."
        ),
        parse_mode=ParseMode.HTML,
    )


def get_handler() -> CommandHandler:
    return CommandHandler(
        "start",
        start,
    )
