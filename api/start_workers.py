#!/usr/bin/env python3
"""
Start Celery workers for async calibration tasks
"""

import os
import sys
import subprocess
import signal
from pathlib import Path

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
        r.ping()
        print("✓ Redis is running")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("Please start Redis with: redis-server")
        return False

def start_celery_worker():
    """Start Celery worker process"""
    try:
        cmd = [
            "celery", "-A", "app.celery_app", "worker",
            "--loglevel=info",
            "--concurrency=2",
            "--hostname=worker@%h"
        ]

        print(f"Starting Celery worker: {' '.join(cmd)}")
        return subprocess.Popen(cmd, cwd=Path(__file__).parent)
    except Exception as e:
        print(f"Failed to start Celery worker: {e}")
        return None

def start_celery_beat():
    """Start Celery beat scheduler for periodic tasks"""
    try:
        cmd = [
            "celery", "-A", "app.celery_app", "beat",
            "--loglevel=info"
        ]

        print(f"Starting Celery beat: {' '.join(cmd)}")
        return subprocess.Popen(cmd, cwd=Path(__file__).parent)
    except Exception as e:
        print(f"Failed to start Celery beat: {e}")
        return None

def main():
    """Main function to start all services"""
    print("VA-Calibration Async Workers Startup")
    print("===================================")

    # Check Redis
    if not check_redis():
        return 1

    # Start processes
    worker_process = start_celery_worker()
    if not worker_process:
        return 1

    beat_process = start_celery_beat()
    if not beat_process:
        worker_process.terminate()
        return 1

    print("\n✓ All services started successfully!")
    print("\nPress Ctrl+C to stop all services...")

    def signal_handler(sig, frame):
        print("\nShutting down services...")
        if worker_process:
            worker_process.terminate()
        if beat_process:
            beat_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Wait for processes
        worker_process.wait()
        beat_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

    return 0

if __name__ == "__main__":
    sys.exit(main())