#!/bin/bash
# Start both the health check server and Celery worker
# This allows the worker to run as a web service on Render's free tier

echo "Starting VA-Calibration Worker Service..."

# Start health check server in background
echo "Starting health check server on port $PORT..."
poetry run python -m app.worker_health &
HEALTH_PID=$!

# Give health server time to start
sleep 2

# Start Celery worker
echo "Starting Celery worker..."
poetry run celery -A app.job_endpoints.celery_app worker --loglevel=info --pool=solo &
CELERY_PID=$!

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
