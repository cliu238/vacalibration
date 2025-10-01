"""Simple health check web server for Celery worker on Render free tier.

This allows the Celery worker to be deployed as a web service instead of
a background worker, which is not available on Render's free tier.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import os

app = FastAPI(title="VA-Calibration Worker Health")


@app.get("/")
@app.get("/health")
async def health_check():
    """Health check endpoint to keep the worker service alive."""
    # Try to check Celery worker status
    celery_status = "unknown"
    worker_count = 0
    broker_connected = False

    try:
        from app.job_endpoints import celery_app
        inspector = celery_app.control.inspect()
        active = inspector.active()

        if active is not None:
            worker_count = len(active)
            celery_status = "connected" if worker_count > 0 else "no_workers"
            broker_connected = True
        else:
            celery_status = "no_workers"

    except Exception as e:
        celery_status = f"error: {str(e)}"

    return JSONResponse({
        "status": "healthy" if broker_connected else "degraded",
        "service": "va-calibration-worker",
        "message": "Celery worker is running",
        "celery_status": celery_status,
        "worker_count": worker_count,
        "broker_connected": broker_connected,
        "broker_url": os.getenv("CELERY_BROKER_URL", "not_set")[:20] + "..." if os.getenv("CELERY_BROKER_URL") else "not_set"
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
