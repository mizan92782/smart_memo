#!/bin/bash
# infra/celery/worker_start.sh
# Start Celery worker for development or production
# Usage: ./infra/celery/worker_start.sh [dev|prod]

set -e

ENV=${1:-dev}
APP="smart_memo"
CONCURRENCY=${CELERY_CONCURRENCY:-4}
LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
LOGFILE="logs/celery_worker.log"

echo "🚀 Starting Celery Worker (env=$ENV, concurrency=$CONCURRENCY)"

if [ "$ENV" = "prod" ]; then
    # Production: daemon mode with log file
    celery -A $APP worker \
        --loglevel=$LOG_LEVEL \
        --concurrency=$CONCURRENCY \
        --logfile=$LOGFILE \
        --pidfile=logs/celery_worker.pid \
        --detach
    echo "✅ Celery worker started in background. Logs: $LOGFILE"
else
    # Development: foreground with colored output
    celery -A $APP worker \
        --loglevel=$LOG_LEVEL \
        --concurrency=$CONCURRENCY
fi
