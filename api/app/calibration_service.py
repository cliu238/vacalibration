#!/usr/bin/env python3
"""
Enhanced calibration service with WebSocket support for real-time progress updates
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from .redis_pubsub import (
    publish_calibration_log,
    publish_calibration_progress,
    publish_calibration_status,
    publish_calibration_result,
    publish_calibration_error
)
from .websocket_handler import (
    send_log_message,
    send_progress_update,
    send_status_update,
    send_result_message,
    send_error_message,
    JobStatus
)
from .r_script_generator import generate_calibration_r_script

# Set up logging
logger = logging.getLogger(__name__)


class CalibrationJob:
    """Represents a calibration job with progress tracking"""

    def __init__(self, job_id: str, request_data: Dict):
        self.job_id = job_id
        self.request_data = request_data
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.stage = "Initializing"
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict] = None
        self.temp_dir: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert job to dictionary representation"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "has_result": self.result is not None
        }


class CalibrationService:
    """Service for managing calibration jobs with real-time updates"""

    def __init__(self):
        self.active_jobs: Dict[str, CalibrationJob] = {}
        self.job_history: List[CalibrationJob] = []

    def create_job(self, request_data: Dict) -> str:
        """Create a new calibration job and return job ID"""
        job_id = str(uuid.uuid4())
        job = CalibrationJob(job_id, request_data)
        self.active_jobs[job_id] = job

        logger.info(f"Created calibration job {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[CalibrationJob]:
        """Get job by ID"""
        return self.active_jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status information"""
        job = self.get_job(job_id)
        return job.to_dict() if job else None

    async def run_calibration(self, job_id: str) -> Dict:
        """Run calibration with real-time progress updates"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.stage = "Preparing data"
            job.progress = 0.0

            # Send initial status update
            await self._send_updates(job_id, "Starting calibration", 0.0, "Preparing data")

            # Create temporary directory
            job.temp_dir = tempfile.mkdtemp(prefix=f"vacalib_{job_id}_")
            await self._send_log(job_id, f"Created temporary directory: {job.temp_dir}")

            # Prepare input files
            await self._send_updates(job_id, "Preparing input data", 10.0, "Writing input files")
            input_file, r_script_file = await self._prepare_input_files(job)

            # Run R calibration with progress monitoring
            await self._send_updates(job_id, "Running R calibration", 20.0, "Executing R script")
            result = await self._run_r_calibration(job, input_file, r_script_file)

            # Process results
            await self._send_updates(job_id, "Processing results", 90.0, "Formatting output")
            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.progress = 100.0

            # Send completion updates
            await self._send_updates(job_id, "Calibration completed successfully", 100.0, "Complete")
            await send_result_message(job_id, result)
            await publish_calibration_result(job_id, result)

            # Move to history
            self._move_to_history(job_id)

            return result

        except Exception as e:
            # Handle errors
            error_message = str(e)
            job.error = error_message
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)

            await self._send_error(job_id, error_message)
            self._move_to_history(job_id)

            raise

        finally:
            # Cleanup temp directory
            if job.temp_dir and os.path.exists(job.temp_dir):
                try:
                    import shutil
                    shutil.rmtree(job.temp_dir)
                    await self._send_log(job_id, f"Cleaned up temporary directory")
                except Exception as e:
                    logger.error(f"Failed to cleanup temp directory: {e}")

    async def _prepare_input_files(self, job: CalibrationJob) -> tuple[str, str]:
        """Prepare input files for R script"""
        input_file = os.path.join(job.temp_dir, "input.json")
        r_script_file = os.path.join(job.temp_dir, "run.R")

        # Prepare request data
        request_data = job.request_data.copy()

        # If no va_data provided, use example (matching Celery endpoint behavior)
        # This works for all cases - R script handles "use_example" marker correctly
        if not request_data.get("va_data"):
            request_data["va_data"] = {"insilicova": "use_example"}

        # Write input file
        with open(input_file, 'w') as f:
            json.dump(request_data, f)

        # Save a copy for debugging
        debug_file = "/tmp/calibration-service-input.json"
        with open(debug_file, 'w') as f:
            json.dump(request_data, f, indent=2)

        # Log the exact JSON being sent to R for debugging
        await self._send_log(job.job_id, f"DEBUG: Input JSON saved to {debug_file}")

        # Write R script with progress reporting (using shared module)
        r_script_content = generate_calibration_r_script()
        await self._send_log(job.job_id, f"R script generated, length: {len(r_script_content)} characters")

        with open(r_script_file, 'w') as f:
            f.write(r_script_content)

        # Verify file was written
        if os.path.exists(r_script_file):
            file_size = os.path.getsize(r_script_file)
            await self._send_log(job.job_id, f"R script file written successfully: {r_script_file} ({file_size} bytes)")
        else:
            await self._send_log(job.job_id, f"ERROR: R script file not created at {r_script_file}")

        await self._send_log(job.job_id, f"Prepared input files: {input_file}, {r_script_file}")

        return input_file, r_script_file

    async def _run_r_calibration(self, job: CalibrationJob, input_file: str, r_script_file: str) -> Dict:
        """Run R calibration with progress monitoring"""
        output_file = os.path.join(job.temp_dir, "output.json")

        # Build command
        cmd = ["Rscript", r_script_file, input_file, output_file, job.job_id]

        await self._send_log(job.job_id, f"Running command: {' '.join(cmd)}")

        # Use synchronous subprocess like Celery endpoint (asyncio version has issues)
        import subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout like Celery
            text=True,
            bufsize=1
        )

        # Read and log output line by line (synchronously)
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # Check for progress indicators
                if "PROGRESS:" in line:
                    try:
                        parts = line.split("PROGRESS:", 1)[1].strip()
                        if "%" in parts:
                            progress_part, stage_part = parts.split("%", 1)
                            progress = float(progress_part.strip())
                            stage = stage_part.strip(" - ")
                            await self._send_updates(job.job_id, f"Progress: {progress}%", progress, stage)
                    except (ValueError, IndexError):
                        pass
                # Log all output
                await self._send_log(job.job_id, line, "info")

        # Wait for completion
        return_code = process.wait()

        # Check results
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                output_data = json.load(f)

            if output_data.get("success"):
                await self._send_log(job.job_id, "R calibration completed successfully")
                return {
                    "status": "success",
                    "uncalibrated": output_data.get("uncalibrated", {}),
                    "calibrated": output_data.get("calibrated", {}),
                    "job_id": job.job_id,
                    "age_group": job.request_data.get("age_group"),
                    "country": job.request_data.get("country")
                }
            else:
                error_msg = output_data.get("error", "Calibration failed")
                await self._send_error(job.job_id, error_msg, "r_script_error")
                raise Exception(error_msg)
        else:
            error_msg = f"R script failed with return code {return_code}"
            await self._send_error(job.job_id, error_msg, "r_script_error")
            raise Exception(error_msg)

    async def _monitor_r_output(self, job_id: str, stdout):
        """Monitor R script stdout for progress updates"""
        try:
            async for line in stdout:
                line_str = line.decode().strip()
                if line_str:
                    # Check for progress indicators
                    if "PROGRESS:" in line_str:
                        try:
                            # Parse progress: "PROGRESS: 45.5% - Loading data"
                            parts = line_str.split("PROGRESS:", 1)[1].strip()
                            if "%" in parts:
                                progress_part, stage_part = parts.split("%", 1)
                                progress = float(progress_part.strip())
                                stage = stage_part.strip(" - ")
                                await self._send_updates(job_id, f"Progress: {progress}%", progress, stage)
                        except (ValueError, IndexError):
                            pass

                    # Log all output
                    await self._send_log(job_id, line_str, "info")

        except Exception as e:
            logger.error(f"Error monitoring R stdout: {e}")

    async def _monitor_r_errors(self, job_id: str, stderr):
        """Monitor R script stderr for errors"""
        try:
            async for line in stderr:
                line_str = line.decode().strip()
                if line_str:
                    await self._send_log(job_id, line_str, "error")

        except Exception as e:
            logger.error(f"Error monitoring R stderr: {e}")

    async def _send_updates(self, job_id: str, message: str, progress: float, stage: str):
        """Send all types of updates"""
        # Update job
        job = self.get_job(job_id)
        if job:
            job.progress = progress
            job.stage = stage

        # Send updates via both channels
        await send_progress_update(job_id, progress, stage)
        await send_status_update(job_id, JobStatus.RUNNING, message)
        await publish_calibration_progress(job_id, progress, stage)
        await publish_calibration_status(job_id, "running", message)

    async def _send_log(self, job_id: str, message: str, level: str = "info"):
        """Send log message via both channels"""
        await send_log_message(job_id, message, level)
        await publish_calibration_log(job_id, message, level)

    async def _send_error(self, job_id: str, error: str, error_type: str = "general"):
        """Send error message via both channels"""
        await send_error_message(job_id, error, error_type)
        await publish_calibration_error(job_id, error, error_type)

    def _move_to_history(self, job_id: str):
        """Move completed job to history"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            self.job_history.append(job)
            del self.active_jobs[job_id]

            # Keep only last 100 jobs in history
            if len(self.job_history) > 100:
                self.job_history = self.job_history[-100:]


# Global service instance
calibration_service = CalibrationService()


def get_calibration_service() -> CalibrationService:
    """Get the global calibration service instance"""
    return calibration_service