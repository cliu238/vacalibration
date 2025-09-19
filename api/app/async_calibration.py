#!/usr/bin/env python3
"""
Async calibration system with Redis-backed job storage and Celery background tasks
"""

import uuid
import json
import subprocess
import tempfile
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Try to import Redis - make it optional for testing
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from fastapi import HTTPException
from pydantic import BaseModel, Field

# Lazy import Celery to avoid connection issues during testing
calibration_task = None

def get_celery_task():
    global calibration_task
    if calibration_task is None:
        try:
            from .celery_app import calibration_task as task
            calibration_task = task
        except Exception:
            pass
    return calibration_task


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CalibrationJob:
    """Calibration job data model"""
    job_id: str
    status: JobStatus
    progress: int  # 0-100
    created_at: datetime
    updated_at: datetime
    request_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    r_output: Optional[List[str]] = None  # Line-by-line R output
    execution_time: Optional[float] = None  # Seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationJob":
        """Create from dictionary"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["status"] = JobStatus(data["status"])
        return cls(**data)


class JobManager:
    """Redis-backed job storage and management"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self.job_prefix = "calibration_job:"
        self.job_list_key = "calibration_jobs"

    @asynccontextmanager
    async def get_redis(self):
        """Get Redis connection with proper cleanup"""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        try:
            yield self._redis
        except Exception as e:
            # Close connection on error
            if self._redis:
                await self._redis.close()
                self._redis = None
            raise e

    async def create_job(self, request_data: Dict[str, Any]) -> CalibrationJob:
        """Create a new calibration job"""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        job = CalibrationJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            progress=0,
            created_at=now,
            updated_at=now,
            request_data=request_data,
            r_output=[]
        )

        await self._store_job(job)
        return job

    async def get_job(self, job_id: str) -> Optional[CalibrationJob]:
        """Retrieve job by ID"""
        async with self.get_redis() as r:
            try:
                job_data = await r.get(f"{self.job_prefix}{job_id}")
                if job_data:
                    return CalibrationJob.from_dict(json.loads(job_data))
                return None
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve job: {str(e)}"
                )

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        r_output_line: Optional[str] = None,
        execution_time: Optional[float] = None
    ) -> CalibrationJob:
        """Update job status and data"""
        job = await self.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Update fields
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if execution_time is not None:
            job.execution_time = execution_time
        if r_output_line is not None:
            if job.r_output is None:
                job.r_output = []
            job.r_output.append(r_output_line)

        job.updated_at = datetime.now(timezone.utc)
        await self._store_job(job)
        return job

    async def list_jobs(self, limit: int = 50, status_filter: Optional[JobStatus] = None) -> List[CalibrationJob]:
        """List recent jobs with optional status filter"""
        async with self.get_redis() as r:
            try:
                # Get all job IDs from sorted set (newest first)
                job_ids = await r.zrevrange(self.job_list_key, 0, limit - 1)

                jobs = []
                for job_id in job_ids:
                    job = await self.get_job(job_id)
                    if job and (status_filter is None or job.status == status_filter):
                        jobs.append(job)

                return jobs[:limit]
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to list jobs: {str(e)}"
                )

    async def delete_job(self, job_id: str) -> bool:
        """Delete job from storage"""
        async with self.get_redis() as r:
            try:
                # Remove from both individual key and sorted set
                job_key = f"{self.job_prefix}{job_id}"
                pipeline = r.pipeline()
                pipeline.delete(job_key)
                pipeline.zrem(self.job_list_key, job_id)
                results = await pipeline.execute()
                return results[0] > 0  # True if job existed
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete job: {str(e)}"
                )

    async def _store_job(self, job: CalibrationJob):
        """Store job in Redis"""
        async with self.get_redis() as r:
            try:
                job_key = f"{self.job_prefix}{job.job_id}"
                job_data = json.dumps(job.to_dict())

                # Store job data and add to sorted set with timestamp for ordering
                timestamp = job.updated_at.timestamp()
                pipeline = r.pipeline()
                pipeline.set(job_key, job_data, ex=86400 * 7)  # 7 day TTL
                pipeline.zadd(self.job_list_key, {job.job_id: timestamp})
                await pipeline.execute()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store job: {str(e)}"
                )

    async def cleanup_old_jobs(self, max_age_days: int = 7):
        """Clean up jobs older than max_age_days"""
        async with self.get_redis() as r:
            try:
                cutoff_timestamp = (datetime.now(timezone.utc).timestamp() -
                                   (max_age_days * 24 * 60 * 60))

                # Get old job IDs
                old_job_ids = await r.zrangebyscore(
                    self.job_list_key,
                    "-inf",
                    cutoff_timestamp
                )

                if old_job_ids:
                    # Delete job data and remove from sorted set
                    pipeline = r.pipeline()
                    for job_id in old_job_ids:
                        pipeline.delete(f"{self.job_prefix}{job_id}")
                    pipeline.zremrangebyscore(self.job_list_key, "-inf", cutoff_timestamp)
                    await pipeline.execute()

                return len(old_job_ids)
            except Exception as e:
                print(f"Error cleaning up old jobs: {e}")
                return 0


# Global job manager instance
job_manager = JobManager()


class AsyncCalibrationRequest(BaseModel):
    """Request model for async calibration"""
    va_data: Optional[Dict[str, Union[List[Dict], List[List[int]], str]]] = Field(
        default=None,
        description="VA data or 'use_example' to use default data"
    )
    age_group: str = Field(
        default="neonate",
        description="Age group: 'neonate' or 'child'"
    )
    country: str = Field(
        default="Mozambique",
        description="Country for calibration"
    )
    mmat_type: str = Field(
        default="prior",
        description="How to utilize misclassification: 'prior' or 'fixed'"
    )
    ensemble: bool = Field(
        default=True,
        description="Whether to perform ensemble calibration"
    )


class JobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str
    created_at: str


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    progress: int
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class JobListResponse(BaseModel):
    """Response model for job listing"""
    jobs: List[JobStatusResponse]
    total: int


class JobOutputResponse(BaseModel):
    """Response model for job output streaming"""
    job_id: str
    r_output: List[str]
    has_more: bool


async def start_async_calibration(request: AsyncCalibrationRequest) -> JobResponse:
    """Start async calibration job"""
    try:
        # Create job
        job = await job_manager.create_job(request.model_dump())

        # Start Celery task
        task = get_celery_task()
        if task:
            task.delay(job.job_id, request.model_dump())

        return JobResponse(
            job_id=job.job_id,
            status=job.status.value,
            message="Calibration job started",
            created_at=job.created_at.isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start calibration job: {str(e)}"
        )


async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get job status and results"""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        result=job.result,
        error=job.error,
        execution_time=job.execution_time
    )


async def list_calibration_jobs(
    limit: int = 50,
    status: Optional[str] = None
) -> JobListResponse:
    """List calibration jobs with optional filtering"""
    status_filter = JobStatus(status) if status else None
    jobs = await job_manager.list_jobs(limit=limit, status_filter=status_filter)

    job_responses = [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            result=job.result,
            error=job.error,
            execution_time=job.execution_time
        )
        for job in jobs
    ]

    return JobListResponse(jobs=job_responses, total=len(job_responses))


async def get_job_output(job_id: str, start_line: int = 0) -> JobOutputResponse:
    """Get R script output for streaming"""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job.r_output:
        return JobOutputResponse(job_id=job_id, r_output=[], has_more=False)

    # Return output from start_line onwards
    output_lines = job.r_output[start_line:]
    has_more = job.status in [JobStatus.PENDING, JobStatus.RUNNING]

    return JobOutputResponse(
        job_id=job_id,
        r_output=output_lines,
        has_more=has_more
    )


async def cancel_job(job_id: str) -> JobStatusResponse:
    """Cancel a running job"""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in {job.status.value} status"
        )

    # Update job status to cancelled
    updated_job = await job_manager.update_job(
        job_id,
        status=JobStatus.CANCELLED,
        error="Job cancelled by user"
    )

    # TODO: Terminate Celery task if possible
    # celery_app.control.revoke(job_id, terminate=True)

    return JobStatusResponse(
        job_id=updated_job.job_id,
        status=updated_job.status.value,
        progress=updated_job.progress,
        created_at=updated_job.created_at.isoformat(),
        updated_at=updated_job.updated_at.isoformat(),
        result=updated_job.result,
        error=updated_job.error,
        execution_time=updated_job.execution_time
    )


async def delete_calibration_job(job_id: str) -> Dict[str, str]:
    """Delete a calibration job"""
    deleted = await job_manager.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {"message": f"Job {job_id} deleted successfully"}


def get_calibration_r_script() -> str:
    """Get the R script for calibration with progress tracking"""
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]

# Progress tracking function
report_progress <- function(message, progress = NULL) {
    if (!is.null(progress)) {
        cat(sprintf("PROGRESS: %d %s\\n", progress, message))
    } else {
        cat(sprintf("INFO: %s\\n", message))
    }
    flush.console()
}

tryCatch({
    report_progress("Starting calibration", 0)

    # Read input
    input_data <- fromJSON(input_file)
    report_progress("Input data loaded", 10)

    # Process VA data
    va_data <- list()
    for (algo in names(input_data$va_data)) {
        data_value <- input_data$va_data[[algo]]

        if (is.character(data_value) && data_value == "use_example") {
            report_progress(sprintf("Loading example data for %s", algo), 20)
            # Load example data
            if (input_data$age_group == "neonate") {
                data(comsamoz_public_broad, envir = environment())
                va_data[[algo]] <- comsamoz_public_broad$data
            } else {
                # Create synthetic child data
                n <- 100
                child_causes <- c("malaria", "pneumonia", "diarrhea", "severe_malnutrition",
                                "hiv", "injury", "other", "other_infections", "nn_causes")
                mat <- matrix(0, nrow=n, ncol=length(child_causes))
                colnames(mat) <- child_causes
                for (i in 1:n) {
                    mat[i, sample(1:length(child_causes), 1)] <- 1
                }
                va_data[[algo]] <- mat
            }
        } else if (is.list(data_value) && length(data_value) > 0 && !is.null(data_value[[1]]$cause)) {
            report_progress(sprintf("Converting specific causes for %s", algo), 30)
            # Convert specific causes to broad causes
            df <- data.frame(
                ID = sapply(data_value, function(x) as.character(ifelse(!is.null(x$ID), x$ID, x$id))),
                cause = sapply(data_value, function(x) as.character(x$cause)),
                stringsAsFactors = FALSE
            )
            va_data[[algo]] <- cause_map(df = df, age_group = input_data$age_group)
        } else {
            va_data[[algo]] <- data_value
        }
    }

    report_progress("VA data processed, starting calibration", 40)

    # Run calibration
    result <- vacalibration(
        va_data = va_data,
        age_group = input_data$age_group,
        country = input_data$country,
        Mmat_type = input_data$mmat_type,
        ensemble = input_data$ensemble,
        verbose = TRUE,
        plot_it = FALSE
    )

    report_progress("Calibration completed, processing results", 80)

    # Prepare output
    output <- list(success = TRUE)

    # Add uncalibrated CSMF
    if (!is.null(result$p_uncalib)) {
        output$uncalibrated <- as.list(result$p_uncalib)
    }

    # Add calibrated results
    if (!is.null(result$pcalib_postsumm)) {
        output$calibrated <- list()
        for (algo in dimnames(result$pcalib_postsumm)[[1]]) {
            output$calibrated[[algo]] <- list(
                mean = as.list(result$pcalib_postsumm[algo, "postmean", ]),
                lower_ci = as.list(result$pcalib_postsumm[algo, "lowcredI", ]),
                upper_ci = as.list(result$pcalib_postsumm[algo, "upcredI", ])
            )
        }
    } else if (!is.null(result$p_calib)) {
        # Handle fixed case
        output$calibrated <- list()
        for (algo in names(result$p_calib)) {
            output$calibrated[[algo]] <- list(
                mean = as.list(result$p_calib[[algo]]),
                lower_ci = as.list(result$p_calib[[algo]]),
                upper_ci = as.list(result$p_calib[[algo]])
            )
        }
    }

    report_progress("Results prepared", 95)

    # Write output
    write(toJSON(output, auto_unbox = TRUE, na = "null"), output_file)

    report_progress("Calibration finished successfully", 100)

}, error = function(e) {
    error_msg <- as.character(e$message)
    cat(sprintf("ERROR: %s\\n", error_msg))
    output <- list(success = FALSE, error = error_msg)
    write(toJSON(output, auto_unbox = TRUE), output_file)
})
'''