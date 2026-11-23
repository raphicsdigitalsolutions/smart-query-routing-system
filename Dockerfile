# Combined production Docker image for Smart Query Routing & Email Automation System.
# Runs FastAPI backend (port 8000 internal/optional) and Next.js 16 frontend/BFF
# (port 3000) under Supervisor as non-root user `app` (UID 10001).
#
# Build from repository root:
#   docker build -t smart-query-system:latest .

FROM node:20-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend-next/package.json frontend-next/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=""
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}
COPY --from=frontend-deps /app/frontend/node_modules ./node_modules
COPY frontend-next/package.json frontend-next/package-lock.json frontend-next/next.config.ts frontend-next/tsconfig.json frontend-next/next-env.d.ts frontend-next/postcss.config.mjs ./
COPY frontend-next/src ./src
COPY frontend-next/public ./public
RUN npm run build

FROM node:20-slim AS frontend-prod-deps
WORKDIR /app/frontend
COPY frontend-next/package.json frontend-next/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund \
    && rm -rf node_modules/playwright node_modules/playwright-core node_modules/@playwright
# Next.js runtime loads next.config.ts when starting; copy typescript without dev tooling.
COPY --from=frontend-deps /app/frontend/node_modules/typescript ./node_modules/typescript

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOME=/home/app \
    ATTACHMENT_STORAGE_DIR=/app/var/attachments \
    API_BASE_URL=http://127.0.0.1:8000/api/v1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app \
    && mkdir -p /app/var/attachments /etc/supervisor/conf.d \
    && chown -R app:app /app/var /home/app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt supervisor \
    && rm -f /tmp/backend-requirements.txt

COPY --from=frontend-deps /usr/local/bin/node /usr/local/bin/node

WORKDIR /app/backend
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/alembic ./alembic
COPY --chown=app:app backend/alembic.ini ./alembic.ini

WORKDIR /app/frontend
COPY --from=frontend-prod-deps --chown=app:app /app/frontend/node_modules ./node_modules
COPY --chown=app:app frontend-next/package.json frontend-next/package-lock.json frontend-next/next.config.ts frontend-next/tsconfig.json frontend-next/next-env.d.ts frontend-next/postcss.config.mjs ./
COPY --from=frontend-builder --chown=app:app /app/frontend/.next ./.next
COPY --chown=app:app frontend-next/public ./public

COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/backend-start.sh /usr/local/bin/backend-start.sh
RUN sed -i 's/\r$//' /usr/local/bin/backend-start.sh /etc/supervisor/conf.d/supervisord.conf \
    && chmod 0644 /etc/supervisor/conf.d/supervisord.conf \
    && chmod 0755 /usr/local/bin/backend-start.sh

USER app
WORKDIR /app

EXPOSE 3000 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); urllib.request.urlopen('http://127.0.0.1:3000/api/health', timeout=3)"]

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
