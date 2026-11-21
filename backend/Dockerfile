# Production image for the FastAPI backend.
# Build from the backend/ directory: docker build -t smartquery-backend ./backend

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ca-certificates is needed for HTTPS calls to OpenAI/SMTP/Meta/Google providers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so source changes do not invalidate this layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Non-root runtime user. No application secret or .env file is copied into the image.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app \
    && mkdir -p /app/var/attachments \
    && chown -R app:app /app/var

COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini

# Idempotent startup script (created here so no extra source file is owned by
# the packaging work). `alembic upgrade head` is safe to re-run; set
# RUN_MIGRATIONS=false for scaled deployments that run migrations as a one-off.
RUN printf '%s\n' \
    '#!/bin/sh' \
    'set -eu' \
    '' \
    'if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then' \
    '  echo "Applying Alembic migrations (upgrade head)..."' \
    '  alembic upgrade head' \
    'else' \
    '  echo "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-unset}); schema must already be current."' \
    'fi' \
    '' \
    'exec "$@"' \
    > /usr/local/bin/docker-entrypoint.sh \
    && chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER app
ENV HOME=/home/app
WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
