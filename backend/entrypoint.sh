#!/bin/bash
set -e

echo "Applying database migrations..."
cd /app
PYTHONPATH=/app alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
