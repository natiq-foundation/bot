# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=docker.io/library/python:3.12-slim

# Build dependencies and wheels in a separate stage so compilers do not ship
# in the final image.
FROM ${PYTHON_IMAGE} AS builder

WORKDIR /build

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=
ARG PIP_TIMEOUT=60
ARG PIP_RETRIES=5

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_TIMEOUT=${PIP_TIMEOUT} \
    PIP_RETRIES=${PIP_RETRIES} \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

# Build the project and all runtime dependencies as wheels.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip wheel --no-cache-dir --wheel-dir=/wheels .

# Runtime image: no compiler toolchain.
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir greenlet
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels natiq-bot \
    && rm -rf /wheels

# Keep Alembic and the source tree available for migrations and app startup.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN chmod 0555 /app/docker-entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
