#!/bin/bash
# Start both the health check server and Celery worker
# This allows the worker to run as a web service on Render's free tier

echo "Starting VA-Calibration Worker Service..."

# Verify environment variables are set
echo "Checking environment variables..."
if [ -z "$CELERY_BROKER_URL" ]; then
    echo "ERROR: CELERY_BROKER_URL not set"
else
    echo "CELERY_BROKER_URL: ${CELERY_BROKER_URL:0:20}..."
fi

if [ -z "$CELERY_RESULT_BACKEND" ]; then
    echo "ERROR: CELERY_RESULT_BACKEND not set"
else
    echo "CELERY_RESULT_BACKEND: ${CELERY_RESULT_BACKEND:0:20}..."
fi

# Explicitly export environment variables for child processes
export CELERY_BROKER_URL
export CELERY_RESULT_BACKEND
export REDIS_URL

# Start health check server in background
echo "Starting health check server on port $PORT..."
poetry run python -m app.worker_health &
HEALTH_PID=$!

# Give health server time to start
sleep 2

# Start Celery worker with verbose logging and calibration queue
echo "Starting Celery worker..."
poetry run celery -A app.job_endpoints.celery_app worker --loglevel=info --pool=solo --queues=calibration &
CELERY_PID=$!

echo "Worker processes started:"
echo "  Health server PID: $HEALTH_PID"
echo "  Celery worker PID: $CELERY_PID"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down worker service..."
    kill $HEALTH_PID 2>/dev/null
    kill $CELERY_PID 2>/dev/null
    exit 0
}

# Trap termination signals
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait
