# Background Workers Setup

## Overview
The VA Calibration API uses Celery with Redis for asynchronous job processing. This allows calibration jobs to run in the background while providing real-time status updates to the frontend.

## Prerequisites
- Redis server running on localhost:6379
- Poetry environment with Celery installed

## Starting the Workers

### Quick Start
```bash
cd api/
./start_workers.sh
```

### Manual Start
```bash
cd api/
poetry run celery -A app.job_endpoints:celery_app worker --loglevel=info --concurrency=2 -Q celery,calibration
```

## Architecture

### Components
1. **Redis** - Message broker and result backend
   - Database 1: Task queue
   - Database 2: Results storage

2. **Celery Workers** - Process calibration tasks
   - Listen on two queues: `celery` (default) and `calibration`
   - Configured with 2 concurrent worker processes

3. **API Server** - Submits tasks to queue
   - Sends calibration tasks to the `calibration` queue
   - Tracks job status in Redis

## Task Flow

1. Frontend creates calibration job via `/jobs/calibrate` endpoint
2. API creates job metadata and stores in Redis
3. API sends task to Celery queue with `queue="calibration"`
4. Worker picks up task and processes it
5. Worker updates job status and logs in Redis
6. Frontend polls for updates or receives via WebSocket

## Job Processing

The main task `run_calibration_task` in `app/job_endpoints.py`:
- Validates job metadata
- Processes calibration using R/OpenVA
- Updates progress periodically
- Logs events for frontend display
- Handles errors and timeouts

## Monitoring

Check worker status:
```bash
# View active tasks
redis-cli -n 1 llen calibration

# View job status
curl http://localhost:8000/jobs/{job_id}
```

## Troubleshooting

### Jobs stuck in pending
- Ensure workers are running: `ps aux | grep celery`
- Check Redis connection: `redis-cli ping`
- Verify queue routing in logs

### Task name errors
- Task must be `app.job_endpoints.run_calibration_task`
- Not `api.app.job_endpoints.run_calibration_task`

### Workers not picking up tasks
- Ensure workers listen to correct queues: `-Q celery,calibration`
- Check task routing in `app/config.py`