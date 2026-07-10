from telegram.ext import Application

from app.bot.handlers.start import start


def register_handlers(application: Application) -> None:
    application.add_handler(start())
