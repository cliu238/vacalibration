#!/usr/bin/env python3
"""Test script to verify Celery is working"""

from celery import Celery
import time

# Create Celery app with same config as main app
celery_app = Celery(
    "vacalibration",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2"
)

# Send a test task
print("Sending task to queue...")
result = celery_app.send_task(
    "app.job_endpoints.run_calibration_task",
    args=["test-job-123", {
        "va_data": {"insilicova": "use_example"},
        "age_group": "neonate",
        "country": "Test",
        "mmat_type": "prior",
        "ensemble": False,
        "priority": 5,
        "timeout_minutes": 30,
        "use_cache": True
    }],
    queue="calibration"  # Specify the queue explicitly
)

print(f"Task ID: {result.id}")
print(f"Task sent to queue 'calibration'")

# Check task state
print(f"Task state: {result.state}")

# Check Redis queues
import redis
r = redis.Redis(host='localhost', port=6379, db=1)
print(f"\nQueue lengths:")
print(f"  celery queue: {r.llen('celery')}")
print(f"  calibration queue: {r.llen('calibration')}")

# List all keys in Redis to see what's there
print(f"\nAll Redis keys in db 1:")
for key in r.keys()[:10]:  # Show first 10 keys
    print(f"  {key.decode('utf-8')}")