#!/bin/bash
# infra/celery/beat_start.sh
# Start Celery Beat (scheduler) for development or production
# Usage: ./infra/celery/beat_start.sh [dev|prod]

set -e

ENV=${1:-dev}
APP="smart_memo"
LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
LOGFILE="logs/celery_beat.log"

echo "⏰ Starting Celery Beat Scheduler (env=$ENV)"

if [ "$ENV" = "prod" ]; then
    celery -A $APP beat \
        --loglevel=$LOG_LEVEL \
        --logfile=$LOGFILE \
        --pidfile=logs/celery_beat.pid \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler \
        --detach
    echo "✅ Celery Beat started in background. Logs: $LOGFILE"
else
    celery -A $APP beat \
        --loglevel=$LOG_LEVEL \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
fi
