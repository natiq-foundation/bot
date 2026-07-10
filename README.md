# Quran Bot

Telegram Quran bot powered by the Natiq API.

## Stack

- Python 3.12
- python-telegram-bot
- PostgreSQL
- SQLAlchemy 2
- Redis
- Docker
- Alembic

## Start

```bash
cp .env.example .env

docker compose up --build


---

# Before the first test

There are still **three code changes** required before the project will actually start successfully:

## 1. Fix `config.py`

We changed `.env.example` to use:

```env
NATIQ_PRIMARY_API
NATIQ_SECONDARY_API
