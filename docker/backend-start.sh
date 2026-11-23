#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying Alembic migrations (upgrade head)..."
    alembic upgrade head
else
    echo "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-unset}); schema must already be current."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
