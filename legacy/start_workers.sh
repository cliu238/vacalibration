#!/bin/bash
# Start Celery workers for VA Calibration API

echo "Starting Celery workers for VA Calibration..."
echo "Workers will listen on both 'celery' and 'calibration' queues"
echo "Press Ctrl+C to stop"

# Navigate to API directory
cd "$(dirname "$0")"

# Start Celery worker
poetry run celery -A app.job_endpoints:celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    -Q celery,calibration

echo "Workers stopped."