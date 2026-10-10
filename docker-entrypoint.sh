#!/bin/sh
set -eu

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-quran_bot}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

printf '%s\n' "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until pg_isready -q \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB"; do
    sleep 2
done
printf '%s\n' "PostgreSQL is accepting connections."

printf '%s\n' "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
until python -c 'import os, socket, sys; s = socket.socket(); s.settimeout(2); rc = s.connect_ex((os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", "6379")))); s.close(); sys.exit(0 if rc == 0 else 1)' >/dev/null 2>&1; do
    sleep 2
done
printf '%s\n' "Redis is accepting connections."

printf '%s\n' "Running database migrations..."
alembic upgrade head

printf '%s\n' "Starting Quran Bot..."
exec python -m app
