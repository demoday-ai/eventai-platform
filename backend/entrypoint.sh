#!/bin/bash
set -e

# Run migrations only for uvicorn (backend), not for celery workers
if [[ "$1" == "uvicorn" ]] || [[ -z "$1" ]]; then
  echo "Applying database migrations..."
  cd /app
  PYTHONPATH=/app alembic upgrade head

  echo "Starting application..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  # For workers: just exec the command
  exec "$@"
fi
