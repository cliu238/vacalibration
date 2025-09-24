#!/usr/bin/env python3
"""
Celery configuration and background tasks for async calibration
"""

import os
import json
import tempfile
import subprocess
import time
import asyncio
from typing import Dict, Any
from celery import Celery
from celery.utils.log import get_task_logger

# Configure Celery
celery_app = Celery(
    "vacalibration",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["app.celery_app"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=3600,  # 1 hour
)

logger = get_task_logger(__name__)


def sync_update_job_status(job_id: str, **kwargs):
    """Synchronous wrapper for updating job status"""
    try:
        # Import here to avoid circular imports
        from .async_calibration import job_manager

        # Create event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async update
        return loop.run_until_complete(
            job_manager.update_job(job_id, **kwargs)
        )
    except Exception as e:
        logger.error(f"Failed to update job {job_id}: {e}")
        return None


def check_r_setup():
    """Check if R and required packages are available"""
    try:
        # Check R
        result = subprocess.run(["which", "Rscript"], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Rscript not found"

        # Check packages
        check_cmd = [
            "Rscript", "-e",
            "if(!require(vacalibration, quietly=TRUE)) stop('vacalibration not found'); if(!require(jsonlite, quietly=TRUE)) stop('jsonlite not found')"
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return False, f"Missing R packages: {result.stderr}"

        return True, "R ready"
    except subprocess.TimeoutExpired:
        return False, "R check timed out"
    except Exception as e:
        return False, str(e)


def parse_r_output_line(line: str):
    """Parse R output line for progress and messages"""
    line = line.strip()
    if line.startswith("PROGRESS:"):
        # Extract progress: "PROGRESS: 50 Processing data"
        parts = line[9:].strip().split(" ", 1)
        if len(parts) >= 1:
            try:
                progress = int(parts[0])
                message = parts[1] if len(parts) > 1 else ""
                return "progress", progress, message
            except ValueError:
                pass
    elif line.startswith("INFO:"):
        return "info", None, line[5:].strip()
    elif line.startswith("ERROR:"):
        return "error", None, line[6:].strip()

    return "output", None, line


@celery_app.task(bind=True)
def calibration_task(self, job_id: str, request_data: Dict[str, Any]):
    """Background task to run R calibration with progress tracking"""

    logger.info(f"Starting calibration job {job_id}")
    start_time = time.time()

    try:
        # Import here to avoid circular import issues
        from .async_calibration import JobStatus, get_calibration_r_script

        # Update job to running
        sync_update_job_status(job_id, status=JobStatus.RUNNING, progress=0)

        # Check R setup
        r_ready, r_msg = check_r_setup()
        if not r_ready:
            error_msg = f"R not ready: {r_msg}"
            logger.error(error_msg)
            sync_update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error=error_msg,
                execution_time=time.time() - start_time
            )
            return {"success": False, "error": error_msg}

        # Create temp directory
        with tempfile.TemporaryDirectory(prefix="vacalib_async_") as tmpdir:
            input_file = os.path.join(tmpdir, "input.json")
            output_file = os.path.join(tmpdir, "output.json")

            # Prepare request data
            if not request_data.get("va_data"):
                request_data["va_data"] = {"insilicova": "use_example"}

            # Write input
            with open(input_file, 'w') as f:
                json.dump(request_data, f)

            # Create R script
            r_script_file = os.path.join(tmpdir, "calibration.R")
            with open(r_script_file, 'w') as f:
                f.write(get_calibration_r_script())

            # Run R script with real-time output capture
            cmd = ["Rscript", r_script_file, input_file, output_file]
            logger.info(f"Running R command: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=os.getcwd()
            )

            # Stream output and track progress
            last_progress = 0
            output_lines = []

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break

                if output:
                    line = output.strip()
                    if line:
                        output_lines.append(line)

                        # Parse line for progress/messages
                        line_type, progress, message = parse_r_output_line(line)

                        if line_type == "progress" and progress is not None:
                            if progress > last_progress:
                                sync_update_job_status(
                                    job_id,
                                    progress=progress,
                                    r_output_line=line
                                )
                                last_progress = progress
                                logger.info(f"Job {job_id} progress: {progress}% - {message}")
                        elif line_type == "error":
                            logger.error(f"R error: {message}")
                            sync_update_job_status(job_id, r_output_line=line)
                        else:
                            # Regular output
                            sync_update_job_status(job_id, r_output_line=line)

            # Wait for process to complete
            return_code = process.poll()
            execution_time = time.time() - start_time

            logger.info(f"R script completed with return code: {return_code}")

            # Check results
            if return_code == 0 and os.path.exists(output_file):
                try:
                    with open(output_file, 'r') as f:
                        output_data = json.load(f)

                    if output_data.get("success"):
                        # Success - update job with results
                        sync_update_job_status(
                            job_id,
                            status=JobStatus.COMPLETED,
                            progress=100,
                            result=output_data,
                            execution_time=execution_time
                        )

                        logger.info(f"Calibration job {job_id} completed successfully in {execution_time:.2f}s")
                        return {"success": True, "result": output_data}
                    else:
                        # R script failed with error in output
                        error_msg = output_data.get("error", "Calibration failed")
                        sync_update_job_status(
                            job_id,
                            status=JobStatus.FAILED,
                            error=error_msg,
                            execution_time=execution_time
                        )

                        logger.error(f"Calibration failed: {error_msg}")
                        return {"success": False, "error": error_msg}

                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse R output: {str(e)}"
                    sync_update_job_status(
                        job_id,
                        status=JobStatus.FAILED,
                        error=error_msg,
                        execution_time=execution_time
                    )
                    return {"success": False, "error": error_msg}
            else:
                # Process failed or no output file
                error_msg = f"R script failed (exit code: {return_code})"
                if output_lines:
                    error_msg += f". Last output: {output_lines[-1]}"

                sync_update_job_status(
                    job_id,
                    status=JobStatus.FAILED,
                    error=error_msg,
                    execution_time=execution_time
                )

                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    except subprocess.TimeoutExpired:
        error_msg = "Calibration timed out"
        sync_update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error=error_msg,
            execution_time=time.time() - start_time
        )
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        sync_update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error=error_msg,
            execution_time=time.time() - start_time
        )
        logger.error(f"Job {job_id} failed with exception: {e}", exc_info=True)
        return {"success": False, "error": error_msg}


@celery_app.task
def cleanup_old_jobs():
    """Periodic task to clean up old jobs"""
    try:
        from .async_calibration import job_manager

        # Create event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Clean up jobs older than 7 days
        cleaned_count = loop.run_until_complete(
            job_manager.cleanup_old_jobs(max_age_days=7)
        )

        logger.info(f"Cleaned up {cleaned_count} old jobs")
        return {"cleaned_jobs": cleaned_count}

    except Exception as e:
        logger.error(f"Failed to clean up old jobs: {e}")
        return {"error": str(e)}


# Periodic task scheduling
celery_app.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'app.celery_app.cleanup_old_jobs',
        'schedule': 3600.0,  # Run every hour
    },
}
celery_app.conf.timezone = 'UTC'


if __name__ == "__main__":
    # Run Celery worker
    celery_app.start()