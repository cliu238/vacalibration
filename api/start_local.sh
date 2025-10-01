#!/bin/bash
# Quick start script for local development
# This script starts all required services for the VA-Calibration API

set -e  # Exit on error

echo "🚀 Starting VA-Calibration Local Development Environment"
echo "========================================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.12+"
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# Check R
if ! command -v R &> /dev/null; then
    echo "❌ R not found. Please install R 4.0+"
    exit 1
fi
echo "✅ R: $(R --version | head -n 1)"

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    echo "❌ Redis not found. Please install Redis"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping &> /dev/null; then
    echo "⚠️  Redis not running. Starting Redis..."
    redis-server &
    sleep 2
fi
echo "✅ Redis: Running"

# Check Poetry
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry"
    exit 1
fi
echo "✅ Poetry: $(poetry --version)"

echo ""
echo "📦 Installing dependencies..."
poetry install

echo ""
echo "🔧 Setting environment variables..."
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
export CELERY_RESULT_BACKEND=redis://localhost:6379/2

echo "   REDIS_URL=$REDIS_URL"
echo "   CELERY_BROKER_URL=$CELERY_BROKER_URL"
echo "   CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND"

echo ""
echo "🌐 Starting services..."
echo ""
echo "Note: Services will run in background. Use 'pkill -f uvicorn' and 'pkill -f celery' to stop."
echo ""

# Start API server
echo "Starting FastAPI server on http://localhost:8000..."
REDIS_URL=$REDIS_URL \
CELERY_BROKER_URL=$CELERY_BROKER_URL \
CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND \
poetry run uvicorn app.main_direct:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

sleep 3

# Start Celery worker
echo "Starting Celery worker..."
REDIS_URL=$REDIS_URL \
CELERY_BROKER_URL=$CELERY_BROKER_URL \
CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND \
poetry run celery -A app.job_endpoints.celery_app worker --loglevel=info --pool=solo --queues=calibration &
CELERY_PID=$!

sleep 3

echo ""
echo "✅ All services started!"
echo ""
echo "📍 Service URLs:"
echo "   - API Server:      http://localhost:8000"
echo "   - API Docs:        http://localhost:8000/docs"
echo "   - Health Check:    http://localhost:8000/"
echo ""
echo "🧪 Test the setup:"
echo "   curl http://localhost:8000/"
echo "   curl http://localhost:8000/debug/celery"
echo ""
echo "📊 Process IDs:"
echo "   - API Server PID:  $API_PID"
echo "   - Celery Worker:   $CELERY_PID"
echo ""
echo "🛑 To stop all services:"
echo "   pkill -f uvicorn && pkill -f celery"
echo ""
echo "💡 Check logs in this terminal or use:"
echo "   tail -f /tmp/vacalibration-api.log"
echo ""
echo "🎉 Ready for development!"
