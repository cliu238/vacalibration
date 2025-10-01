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
    return JSONResponse({
        "status": "healthy",
        "service": "va-calibration-worker",
        "message": "Celery worker is running"
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
