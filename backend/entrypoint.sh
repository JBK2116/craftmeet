#!/bin/sh
set -e
echo "running alembic database migrations"
uv run alembic upgrade head
echo "migrations successfully ran"

echo "starting application"
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
