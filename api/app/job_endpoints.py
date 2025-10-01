#!/usr/bin/env python3
"""
VA-Calibration API - Job Management Endpoints
Provides comprehensive job orchestration, batch processing, and result caching
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from datetime import datetime, timedelta
import uuid
import json
import tempfile
import os
import subprocess
import asyncio
import redis
import hashlib
from celery import Celery
from celery.result import AsyncResult

from .r_script_generator import generate_calibration_r_script

# Initialize Redis client for caching and job storage
# Use REDIS_URL if available (for Upstash or other hosted Redis)
# Fall back to REDIS_HOST/PORT for local development
redis_url = os.getenv("REDIS_URL")
if redis_url:
    redis_client = redis.from_url(redis_url, decode_responses=True)
else:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )

# Initialize Celery for background job processing
celery_app = Celery(
    "vacalibration",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
)

# Constants
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour default
MAX_LOG_ENTRIES = 1000
BATCH_MAX_SIZE = 50


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class LogLevel(str, Enum):
    """Log entry levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AgeGroup(str, Enum):
    """Age groups for calibration"""
    NEONATE = "neonate"
    CHILD = "child"


class JobLogEntry(BaseModel):
    """Individual log entry for a job"""
    timestamp: datetime = Field(description="Log entry timestamp")
    level: LogLevel = Field(description="Log level")
    message: str = Field(description="Log message")
    component: Optional[str] = Field(default=None, description="Component that generated the log")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional log data")


class JobProgress(BaseModel):
    """Job progress information"""
    current_step: int = Field(description="Current step number", ge=0)
    total_steps: int = Field(description="Total number of steps", gt=0)
    step_name: str = Field(description="Name of current step")
    progress_percentage: float = Field(description="Progress as percentage", ge=0, le=100)
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")


class JobMetadata(BaseModel):
    """Job metadata and configuration"""
    job_id: str = Field(description="Unique job identifier")
    job_type: str = Field(description="Type of job (calibration, batch, etc.)")
    created_at: datetime = Field(description="Job creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    timeout_at: Optional[datetime] = Field(default=None, description="Job timeout timestamp")
    priority: int = Field(default=5, description="Job priority (1-10, higher = more priority)", ge=1, le=10)
    retry_count: int = Field(default=0, description="Number of retry attempts", ge=0)
    max_retries: int = Field(default=3, description="Maximum retry attempts", ge=0)


class CalibrationJobRequest(BaseModel):
    """Request model for calibration job"""
    va_data: Optional[Dict[str, Union[List[Dict], List[List[int]], str]]] = Field(
        default=None,
        description="VA data or 'use_example' to use default data"
    )
    age_group: AgeGroup = Field(
        default=AgeGroup.NEONATE,
        description="Age group: 'neonate' or 'child'"
    )
    country: str = Field(
        default="Mozambique",
        description="Country for calibration"
    )
    mmat_type: str = Field(
        default="prior",
        description="Misclassification matrix type: 'prior' or 'fixed'"
    )
    ensemble: bool = Field(
        default=True,
        description="Whether to perform ensemble calibration"
    )
    priority: int = Field(
        default=5,
        description="Job priority (1-10)",
        ge=1,
        le=10
    )
    timeout_minutes: int = Field(
        default=30,
        description="Job timeout in minutes",
        ge=1,
        le=120
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use cached results if available"
    )


class BatchCalibrationRequest(BaseModel):
    """Request model for batch calibration jobs"""
    jobs: List[CalibrationJobRequest] = Field(
        description="List of calibration jobs to process",
        min_items=1,
        max_items=BATCH_MAX_SIZE
    )
    batch_name: Optional[str] = Field(default=None, description="Optional batch identifier")
    parallel_limit: int = Field(
        default=5,
        description="Maximum number of parallel jobs",
        ge=1,
        le=10
    )
    fail_fast: bool = Field(
        default=False,
        description="Stop batch processing on first job failure"
    )

    @validator('jobs')
    def validate_batch_size(cls, v):
        if len(v) > BATCH_MAX_SIZE:
            raise ValueError(f"Batch size cannot exceed {BATCH_MAX_SIZE} jobs")
        return v


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str = Field(description="Job identifier")
    status: JobStatus = Field(description="Current job status")
    progress: Optional[JobProgress] = Field(default=None, description="Job progress information")
    metadata: JobMetadata = Field(description="Job metadata")
    logs: List[JobLogEntry] = Field(description="Job execution logs")
    result_summary: Optional[Dict[str, Any]] = Field(default=None, description="Brief result summary")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Error information if failed")


class JobListFilter(BaseModel):
    """Filter parameters for job listing"""
    status: Optional[JobStatus] = Field(default=None, description="Filter by job status")
    job_type: Optional[str] = Field(default=None, description="Filter by job type")
    age_group: Optional[AgeGroup] = Field(default=None, description="Filter by age group")
    country: Optional[str] = Field(default=None, description="Filter by country")
    created_after: Optional[datetime] = Field(default=None, description="Filter jobs created after date")
    created_before: Optional[datetime] = Field(default=None, description="Filter jobs created before date")


class JobListResponse(BaseModel):
    """Response model for job listing"""
    jobs: List[JobMetadata] = Field(description="List of jobs matching filter criteria")
    total_count: int = Field(description="Total number of jobs matching filters")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of jobs per page")
    has_next: bool = Field(description="Whether there are more pages available")


class JobResultResponse(BaseModel):
    """Response model for job results"""
    job_id: str = Field(description="Job identifier")
    status: JobStatus = Field(description="Job status")
    result: Dict[str, Any] = Field(description="Calibration results")
    metadata: JobMetadata = Field(description="Job metadata")
    cache_info: Optional[Dict[str, Any]] = Field(default=None, description="Cache information")


class BatchJobResponse(BaseModel):
    """Response model for batch job creation"""
    batch_id: str = Field(description="Batch identifier")
    job_ids: List[str] = Field(description="List of created job IDs")
    batch_metadata: Dict[str, Any] = Field(description="Batch processing metadata")


class BatchStatusResponse(BaseModel):
    """Response model for batch status"""
    batch_id: str = Field(description="Batch identifier")
    total_jobs: int = Field(description="Total number of jobs in batch")
    completed_jobs: int = Field(description="Number of completed jobs")
    failed_jobs: int = Field(description="Number of failed jobs")
    running_jobs: int = Field(description="Number of currently running jobs")
    pending_jobs: int = Field(description="Number of pending jobs")
    batch_status: str = Field(description="Overall batch status")
    job_statuses: List[Dict[str, str]] = Field(description="Individual job statuses")


class CacheStats(BaseModel):
    """Cache statistics response"""
    total_cached_results: int = Field(description="Total number of cached results")
    cache_hit_rate: float = Field(description="Cache hit rate percentage")
    total_cache_size_mb: float = Field(description="Total cache size in MB")
    oldest_cached_result: Optional[datetime] = Field(default=None, description="Timestamp of oldest cached result")
    newest_cached_result: Optional[datetime] = Field(default=None, description="Timestamp of newest cached result")


# Helper functions
def generate_job_id() -> str:
    """Generate unique job ID"""
    return f"job_{uuid.uuid4().hex[:12]}"


def generate_batch_id() -> str:
    """Generate unique batch ID"""
    return f"batch_{uuid.uuid4().hex[:12]}"


def get_cache_key(request_data: Dict[str, Any]) -> str:
    """Generate cache key for calibration request"""
    # Create deterministic hash of request parameters
    cache_data = {
        "va_data": request_data.get("va_data"),
        "age_group": request_data.get("age_group"),
        "country": request_data.get("country"),
        "mmat_type": request_data.get("mmat_type"),
        "ensemble": request_data.get("ensemble")
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    return f"calibration_result:{hashlib.md5(cache_str.encode()).hexdigest()}"


def log_job_event(job_id: str, level: LogLevel, message: str, component: str = None, data: Dict[str, Any] = None):
    """Log an event for a job"""
    log_entry = JobLogEntry(
        timestamp=datetime.utcnow(),
        level=level,
        message=message,
        component=component,
        data=data
    )

    # Store in Redis with job logs
    log_key = f"job_logs:{job_id}"
    redis_client.lpush(log_key, log_entry.model_dump_json())
    redis_client.ltrim(log_key, 0, MAX_LOG_ENTRIES - 1)  # Keep only recent logs
    redis_client.expire(log_key, CACHE_TTL * 24)  # Keep logs longer than results

    # Publish to Redis channel for WebSocket broadcasting
    try:
        channel = f"job:{job_id}:logs"
        message_data = {
            "type": "log",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "line": message,
                "level": level.value,
                "source": component or "system"
            }
        }
        redis_client.publish(channel, json.dumps(message_data))
    except Exception as e:
        # Don't fail the job if Redis publish fails
        logger.warning(f"Failed to publish log to Redis channel: {e}")


def update_job_progress(job_id: str, current_step: int, total_steps: int, step_name: str):
    """Update job progress"""
    progress_percentage = (current_step / total_steps) * 100
    progress = JobProgress(
        current_step=current_step,
        total_steps=total_steps,
        step_name=step_name,
        progress_percentage=progress_percentage
    )

    progress_key = f"job_progress:{job_id}"
    redis_client.set(progress_key, progress.model_dump_json(), ex=CACHE_TTL)


def get_job_metadata(job_id: str) -> Optional[JobMetadata]:
    """Retrieve job metadata from Redis"""
    metadata_key = f"job_metadata:{job_id}"
    metadata_data = redis_client.get(metadata_key)
    if metadata_data:
        return JobMetadata.model_validate_json(metadata_data)
    return None


def store_job_metadata(job_id: str, metadata: JobMetadata):
    """Store job metadata in Redis"""
    metadata_key = f"job_metadata:{job_id}"
    redis_client.set(metadata_key, metadata.model_dump_json(), ex=CACHE_TTL * 24)


def get_job_progress(job_id: str) -> Optional[JobProgress]:
    """Retrieve job progress from Redis"""
    progress_key = f"job_progress:{job_id}"
    progress_data = redis_client.get(progress_key)
    if progress_data:
        return JobProgress.model_validate_json(progress_data)
    return None


def get_job_logs(job_id: str, level_filter: LogLevel = None, limit: int = 100, offset: int = 0) -> List[JobLogEntry]:
    """Retrieve job logs from Redis"""
    log_key = f"job_logs:{job_id}"
    log_entries = redis_client.lrange(log_key, offset, offset + limit - 1)

    logs = []
    for entry_data in log_entries:
        try:
            log_entry = JobLogEntry.model_validate_json(entry_data)
            if level_filter is None or log_entry.level == level_filter:
                logs.append(log_entry)
        except Exception:
            continue  # Skip malformed log entries

    return logs


def store_job_result(job_id: str, result: Dict[str, Any], use_cache: bool = True):
    """Store job result in Redis"""
    result_key = f"job_result:{job_id}"
    redis_client.set(result_key, json.dumps(result), ex=CACHE_TTL * 24)

    # Also cache by request hash if caching is enabled
    if use_cache:
        metadata = get_job_metadata(job_id)
        if metadata:
            request_data = redis_client.get(f"job_request:{job_id}")
            if request_data:
                cache_key = get_cache_key(json.loads(request_data))
                cache_data = {
                    "result": result,
                    "cached_at": datetime.utcnow().isoformat(),
                    "job_id": job_id
                }
                redis_client.set(cache_key, json.dumps(cache_data), ex=CACHE_TTL)


def get_cached_result(request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retrieve cached result if available"""
    cache_key = get_cache_key(request_data)
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None


# Celery tasks
@celery_app.task(bind=True)
def run_calibration_task(self, job_id: str, request_data: Dict[str, Any]):
    """Celery task to run calibration job"""
    try:
        # Update job status to running
        metadata = get_job_metadata(job_id)
        if not metadata:
            raise ValueError(f"Job metadata not found for {job_id}")

        metadata.started_at = datetime.utcnow()
        store_job_metadata(job_id, metadata)

        log_job_event(job_id, LogLevel.INFO, "Starting calibration job", "celery_worker")
        update_job_progress(job_id, 1, 5, "Initializing")

        # Check for cached result
        if request_data.get("use_cache", True):
            cached_result = get_cached_result(request_data)
            if cached_result:
                log_job_event(job_id, LogLevel.INFO, "Using cached result", "cache")
                update_job_progress(job_id, 5, 5, "Completed (cached)")

                metadata.completed_at = datetime.utcnow()
                store_job_metadata(job_id, metadata)

                result = cached_result["result"]
                result["cache_info"] = {
                    "cached_at": cached_result["cached_at"],
                    "source_job_id": cached_result["job_id"]
                }

                store_job_result(job_id, result, use_cache=False)  # Don't re-cache
                return {"status": "success", "result": result}

        # Prepare R execution
        update_job_progress(job_id, 2, 5, "Preparing data")
        log_job_event(job_id, LogLevel.INFO, "Preparing R execution environment", "r_processor")

        with tempfile.TemporaryDirectory(prefix=f"vacalib_{job_id}_") as tmpdir:
            input_file = os.path.join(tmpdir, "input.json")
            output_file = os.path.join(tmpdir, "output.json")

            # Prepare request data for R
            if not request_data.get("va_data"):
                request_data["va_data"] = {"insilicova": "use_example"}

            with open(input_file, 'w') as f:
                json.dump(request_data, f)

            # Save a copy for debugging
            debug_file = "/tmp/celery-input.json"
            with open(debug_file, 'w') as f:
                json.dump(request_data, f, indent=2)

            update_job_progress(job_id, 3, 5, "Running R calibration")
            log_job_event(job_id, LogLevel.INFO, "Executing R calibration script", "r_processor")

            # Create R script (using shared module)
            r_script_file = os.path.join(tmpdir, "run.R")
            with open(r_script_file, 'w') as f:
                f.write(generate_calibration_r_script())

            # Run R script with real-time log streaming
            timeout_minutes = request_data.get("timeout_minutes", 30)
            cmd = ["Rscript", r_script_file, input_file, output_file, job_id]

            # Simple subprocess with line-by-line output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1
            )

            # Read and log output line by line
            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    # Send to Redis immediately
                    log_job_event(job_id, LogLevel.INFO, line, "R_console")

            # Wait for process to complete
            process.wait(timeout=timeout_minutes * 60)

            # Create result object
            class ProcessResult:
                def __init__(self, returncode, stdout):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = ""

            result = ProcessResult(process.returncode, '\n'.join(output_lines))

            update_job_progress(job_id, 4, 5, "Processing results")

            # Process output
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    output_data = json.load(f)

                if output_data.get("success"):
                    log_job_event(job_id, LogLevel.INFO, "Calibration completed successfully", "r_processor")

                    result_data = {
                        "status": "success",
                        "uncalibrated": output_data.get("uncalibrated", {}),
                        "calibrated": output_data.get("calibrated", {}),
                        "age_group": request_data["age_group"],
                        "country": request_data["country"],
                        "completed_at": datetime.utcnow().isoformat()
                    }

                    store_job_result(job_id, result_data, request_data.get("use_cache", True))
                    update_job_progress(job_id, 5, 5, "Completed")

                    metadata.completed_at = datetime.utcnow()
                    store_job_metadata(job_id, metadata)

                    return {"status": "success", "result": result_data}
                else:
                    error_msg = output_data.get("error", "R calibration failed")
                    log_job_event(job_id, LogLevel.ERROR, f"R calibration failed: {error_msg}", "r_processor")
                    raise Exception(error_msg)
            else:
                error_msg = f"R script failed: {result.stderr or result.stdout}"
                log_job_event(job_id, LogLevel.ERROR, error_msg, "r_processor")
                raise Exception(error_msg)

    except subprocess.TimeoutExpired:
        log_job_event(job_id, LogLevel.ERROR, "Job timed out", "celery_worker")
        metadata = get_job_metadata(job_id)
        if metadata:
            metadata.completed_at = datetime.utcnow()
            store_job_metadata(job_id, metadata)
        return {"status": "timeout", "error": "Job execution timed out"}

    except Exception as e:
        log_job_event(job_id, LogLevel.ERROR, f"Job failed: {str(e)}", "celery_worker")
        metadata = get_job_metadata(job_id)
        if metadata:
            metadata.completed_at = datetime.utcnow()
            store_job_metadata(job_id, metadata)
        return {"status": "failed", "error": str(e)}



async def get_job_status(job_id: str, log_level: Optional[LogLevel] = None, log_limit: int = 100, log_offset: int = 0) -> JobStatusResponse:
    """Get comprehensive job status with logs and progress"""

    # Get job metadata
    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Get job progress
    progress = get_job_progress(job_id)

    # Get job logs with filtering
    logs = get_job_logs(job_id, log_level, log_limit, log_offset)

    # Get Celery task status
    celery_result = AsyncResult(job_id, app=celery_app)

    # Determine job status
    if celery_result.state == "PENDING":
        status = JobStatus.PENDING
    elif celery_result.state == "STARTED":
        status = JobStatus.RUNNING
    elif celery_result.state == "SUCCESS":
        status = JobStatus.SUCCESS
    elif celery_result.state == "FAILURE":
        status = JobStatus.FAILED
    elif celery_result.state == "REVOKED":
        status = JobStatus.CANCELLED
    else:
        status = JobStatus.PENDING

    # Get result summary if completed
    result_summary = None
    error_details = None

    if status == JobStatus.SUCCESS:
        result_data = redis_client.get(f"job_result:{job_id}")
        if result_data:
            full_result = json.loads(result_data)
            result_summary = {
                "algorithms_processed": len(full_result.get("calibrated", {})),
                "age_group": full_result.get("age_group"),
                "country": full_result.get("country"),
                "completion_time": full_result.get("completed_at")
            }
    elif status == JobStatus.FAILED and celery_result.failed():
        error_details = {
            "error_type": type(celery_result.result).__name__ if celery_result.result else "Unknown",
            "error_message": str(celery_result.result) if celery_result.result else "Job failed",
            "traceback": celery_result.traceback if hasattr(celery_result, 'traceback') else None
        }

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        progress=progress,
        metadata=metadata,
        logs=logs,
        result_summary=result_summary,
        error_details=error_details
    )


async def create_calibration_job(request: CalibrationJobRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Create a new calibration job"""

    job_id = generate_job_id()

    # Create job metadata
    timeout_at = datetime.utcnow() + timedelta(minutes=request.timeout_minutes)
    metadata = JobMetadata(
        job_id=job_id,
        job_type="calibration",
        created_at=datetime.utcnow(),
        timeout_at=timeout_at,
        priority=request.priority
    )

    # Store job metadata and request
    store_job_metadata(job_id, metadata)
    redis_client.set(f"job_request:{job_id}", request.model_dump_json(), ex=CACHE_TTL * 24)

    # Initialize job progress
    update_job_progress(job_id, 0, 5, "Queued")
    log_job_event(job_id, LogLevel.INFO, f"Job created with priority {request.priority}", "api")

    # Submit to Celery with custom task ID
    request_data = request.model_dump()
    celery_app.send_task(
        "app.job_endpoints.run_calibration_task",
        args=[job_id, request_data],
        task_id=job_id,
        priority=request.priority,
        queue="calibration"
    )

    return {"job_id": job_id, "status": "created"}


async def create_batch_jobs(request: BatchCalibrationRequest) -> BatchJobResponse:
    """Create multiple calibration jobs for batch processing"""

    batch_id = generate_batch_id()
    job_ids = []

    # Create individual jobs
    for i, job_request in enumerate(request.jobs):
        job_id = generate_job_id()
        job_ids.append(job_id)

        # Create metadata with batch reference
        timeout_at = datetime.utcnow() + timedelta(minutes=job_request.timeout_minutes)
        metadata = JobMetadata(
            job_id=job_id,
            job_type="batch_calibration",
            created_at=datetime.utcnow(),
            timeout_at=timeout_at,
            priority=job_request.priority
        )

        # Store job metadata and request
        store_job_metadata(job_id, metadata)
        redis_client.set(f"job_request:{job_id}", job_request.model_dump_json(), ex=CACHE_TTL * 24)

        # Initialize progress and logs
        update_job_progress(job_id, 0, 5, "Queued (batch)")
        log_job_event(job_id, LogLevel.INFO, f"Job created as part of batch {batch_id}", "batch_api")

        # Submit to Celery
        request_data = job_request.model_dump()
        celery_app.send_task(
            "app.job_endpoints.run_calibration_task",
            args=[job_id, request_data],
            task_id=job_id,
            priority=job_request.priority,
            queue="calibration"
        )

    # Store batch metadata
    batch_metadata = {
        "batch_id": batch_id,
        "batch_name": request.batch_name,
        "total_jobs": len(job_ids),
        "created_at": datetime.utcnow().isoformat(),
        "parallel_limit": request.parallel_limit,
        "fail_fast": request.fail_fast
    }

    redis_client.set(f"batch_metadata:{batch_id}", json.dumps(batch_metadata), ex=CACHE_TTL * 24)
    redis_client.set(f"batch_jobs:{batch_id}", json.dumps(job_ids), ex=CACHE_TTL * 24)

    return BatchJobResponse(
        batch_id=batch_id,
        job_ids=job_ids,
        batch_metadata=batch_metadata
    )


async def list_jobs(
    filters: JobListFilter,
    page: int = 1,
    page_size: int = 20
) -> JobListResponse:
    """List jobs with filtering and pagination"""

    # Get all job metadata keys
    job_keys = redis_client.keys("job_metadata:*")
    all_jobs = []

    for key in job_keys:
        metadata_data = redis_client.get(key)
        if metadata_data:
            try:
                metadata = JobMetadata.model_validate_json(metadata_data)

                # Apply filters
                if filters.status:
                    # Get Celery status for comparison
                    celery_result = AsyncResult(metadata.job_id, app=celery_app)
                    job_status = _map_celery_status(celery_result.state)
                    if job_status != filters.status:
                        continue

                if filters.job_type and metadata.job_type != filters.job_type:
                    continue

                if filters.created_after and metadata.created_at < filters.created_after:
                    continue

                if filters.created_before and metadata.created_at > filters.created_before:
                    continue

                # Check request-specific filters
                if filters.age_group or filters.country:
                    request_data = redis_client.get(f"job_request:{metadata.job_id}")
                    if request_data:
                        request_obj = json.loads(request_data)
                        if filters.age_group and request_obj.get("age_group") != filters.age_group:
                            continue
                        if filters.country and request_obj.get("country") != filters.country:
                            continue

                all_jobs.append(metadata)

            except Exception:
                continue  # Skip malformed metadata

    # Sort by creation time (newest first)
    all_jobs.sort(key=lambda x: x.created_at, reverse=True)

    # Pagination
    total_count = len(all_jobs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_jobs = all_jobs[start_idx:end_idx]
    has_next = end_idx < total_count

    return JobListResponse(
        jobs=page_jobs,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next
    )


async def list_celery_jobs_simple(limit: int = 50, status: Optional[str] = None) -> Dict[str, Any]:
    """List Celery jobs in simple format for frontend"""

    # Get all job metadata keys
    job_keys = redis_client.keys("job_metadata:*")
    all_jobs = []

    for key in job_keys:
        metadata_data = redis_client.get(key)
        if not metadata_data:
            continue

        try:
            metadata = json.loads(metadata_data)
            job_id = metadata.get("job_id")

            # Get Celery task status
            celery_result = AsyncResult(job_id, app=celery_app)

            # Map Celery status to our status
            if celery_result.state == "PENDING":
                job_status = "pending"
            elif celery_result.state == "STARTED":
                job_status = "running"
            elif celery_result.state == "SUCCESS":
                job_status = "completed"
            elif celery_result.state == "FAILURE":
                job_status = "failed"
            elif celery_result.state == "REVOKED":
                job_status = "cancelled"
            else:
                job_status = "pending"

            # Apply status filter if provided
            if status and job_status != status:
                continue

            # Get progress
            progress_data = redis_client.get(f"job_progress:{job_id}")
            progress_percentage = 0
            if progress_data:
                progress_obj = json.loads(progress_data)
                progress_percentage = progress_obj.get("progress_percentage", 0)

            # Get request data for additional info
            request_data = redis_client.get(f"job_request:{job_id}")
            dataset = None
            algorithm = None
            age_group = None
            country = None
            if request_data:
                request_obj = json.loads(request_data)
                dataset = request_obj.get("dataset", "Unknown Dataset")
                algorithm = request_obj.get("algorithm", "InSilicoVA")
                age_group = request_obj.get("age_group")
                country = request_obj.get("country")

            # Build job object
            job_obj = {
                "job_id": job_id,
                "status": job_status,
                "progress": progress_percentage,
                "created_at": metadata.get("created_at"),
                "completed_at": metadata.get("completed_at"),
                "algorithm": algorithm,
                "dataset": dataset,
                "age_group": age_group,
                "country": country
            }

            # Add error if failed
            if job_status == "failed" and celery_result.failed():
                job_obj["error"] = str(celery_result.result) if celery_result.result else "Job failed"

            all_jobs.append(job_obj)

        except Exception as e:
            continue  # Skip malformed metadata

    # Sort by creation time (newest first)
    all_jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Limit results
    limited_jobs = all_jobs[:limit]

    return {"jobs": limited_jobs, "total": len(limited_jobs)}


async def cancel_job(job_id: str) -> Dict[str, str]:
    """Cancel a running job"""

    # Check if job exists
    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Revoke Celery task
    celery_app.control.revoke(job_id, terminate=True)

    # Log cancellation
    log_job_event(job_id, LogLevel.WARNING, "Job cancelled by user", "api")

    # Update metadata
    metadata.completed_at = datetime.utcnow()
    store_job_metadata(job_id, metadata)

    return {"job_id": job_id, "status": "cancelled"}


async def get_job_result(job_id: str) -> JobResultResponse:
    """Get final results for a completed job"""

    # Check if job exists
    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Get Celery task status
    celery_result = AsyncResult(job_id, app=celery_app)
    status = _map_celery_status(celery_result.state)

    if status not in [JobStatus.SUCCESS, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed (status: {status})")

    # Get result data
    result_data = redis_client.get(f"job_result:{job_id}")
    if not result_data:
        raise HTTPException(status_code=404, detail=f"Results not found for job {job_id}")

    result = json.loads(result_data)

    # Check for cache info
    cache_info = result.get("cache_info")

    return JobResultResponse(
        job_id=job_id,
        status=status,
        result=result,
        metadata=metadata,
        cache_info=cache_info
    )


async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """Get status of batch job processing"""

    # Get batch metadata
    batch_data = redis_client.get(f"batch_metadata:{batch_id}")
    if not batch_data:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    batch_metadata = json.loads(batch_data)

    # Get job IDs
    job_ids_data = redis_client.get(f"batch_jobs:{batch_id}")
    if not job_ids_data:
        raise HTTPException(status_code=404, detail=f"Batch jobs not found for {batch_id}")

    job_ids = json.loads(job_ids_data)

    # Check status of each job
    job_statuses = []
    completed_jobs = 0
    failed_jobs = 0
    running_jobs = 0
    pending_jobs = 0

    for job_id in job_ids:
        celery_result = AsyncResult(job_id, app=celery_app)
        status = _map_celery_status(celery_result.state)

        job_statuses.append({
            "job_id": job_id,
            "status": status.value
        })

        if status == JobStatus.SUCCESS:
            completed_jobs += 1
        elif status == JobStatus.FAILED:
            failed_jobs += 1
        elif status == JobStatus.RUNNING:
            running_jobs += 1
        else:
            pending_jobs += 1

    # Determine overall batch status
    if completed_jobs == len(job_ids):
        batch_status = "completed"
    elif failed_jobs > 0 and batch_metadata.get("fail_fast", False):
        batch_status = "failed"
    elif running_jobs > 0:
        batch_status = "running"
    elif pending_jobs > 0:
        batch_status = "pending"
    else:
        batch_status = "partial"

    return BatchStatusResponse(
        batch_id=batch_id,
        total_jobs=len(job_ids),
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        running_jobs=running_jobs,
        pending_jobs=pending_jobs,
        batch_status=batch_status,
        job_statuses=job_statuses
    )


async def get_cache_statistics() -> CacheStats:
    """Get cache statistics and metrics"""

    # Get all cache keys
    cache_keys = redis_client.keys("calibration_result:*")
    total_cached = len(cache_keys)

    if total_cached == 0:
        return CacheStats(
            total_cached_results=0,
            cache_hit_rate=0.0,
            total_cache_size_mb=0.0
        )

    # Calculate cache size and timestamps
    total_size_bytes = 0
    timestamps = []

    for key in cache_keys:
        cached_data = redis_client.get(key)
        if cached_data:
            total_size_bytes += len(cached_data.encode('utf-8'))
            try:
                cache_obj = json.loads(cached_data)
                if "cached_at" in cache_obj:
                    timestamps.append(datetime.fromisoformat(cache_obj["cached_at"]))
            except:
                continue

    total_size_mb = total_size_bytes / (1024 * 1024)

    # Get cache hit statistics (simplified - would need more tracking in production)
    cache_hit_rate = 0.0  # Would track this with additional counters

    oldest_result = min(timestamps) if timestamps else None
    newest_result = max(timestamps) if timestamps else None

    return CacheStats(
        total_cached_results=total_cached,
        cache_hit_rate=cache_hit_rate,
        total_cache_size_mb=round(total_size_mb, 2),
        oldest_cached_result=oldest_result,
        newest_cached_result=newest_result
    )


async def clear_cache(age_group: Optional[AgeGroup] = None, country: Optional[str] = None) -> Dict[str, Any]:
    """Clear cached results with optional filtering"""

    cache_keys = redis_client.keys("calibration_result:*")
    cleared_count = 0

    for key in cache_keys:
        should_clear = True

        if age_group or country:
            # Would need to decode cache key or store additional metadata for filtering
            # For now, clear all if any filter is specified
            should_clear = True

        if should_clear:
            redis_client.delete(key)
            cleared_count += 1

    return {
        "cleared_results": cleared_count,
        "message": f"Cleared {cleared_count} cached results"
    }


def _map_celery_status(celery_state: str) -> JobStatus:
    """Map Celery task state to JobStatus enum"""
    mapping = {
        "PENDING": JobStatus.PENDING,
        "STARTED": JobStatus.RUNNING,
        "SUCCESS": JobStatus.SUCCESS,
        "FAILURE": JobStatus.FAILED,
        "REVOKED": JobStatus.CANCELLED,
        "RETRY": JobStatus.RUNNING
    }
    return mapping.get(celery_state, JobStatus.PENDING)


async def delete_job(job_id: str) -> Dict[str, str]:
    """Delete a job and all its associated data from Redis"""

    # Check if job exists
    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Revoke Celery task if still running
    celery_result = AsyncResult(job_id, app=celery_app)
    if celery_result.state in ["PENDING", "STARTED"]:
        celery_app.control.revoke(job_id, terminate=True)

    # Delete all Redis keys associated with this job
    keys_to_delete = [
        f"job_metadata:{job_id}",
        f"job_request:{job_id}",
        f"job_progress:{job_id}",
        f"job_logs:{job_id}",
        f"job_result:{job_id}"
    ]

    deleted_count = 0
    for key in keys_to_delete:
        if redis_client.delete(key):
            deleted_count += 1

    log_job_event(job_id, LogLevel.INFO, "Job deleted by user", "api")

    return {
        "job_id": job_id,
        "status": "deleted",
        "deleted_keys": deleted_count
    }


async def delete_all_jobs(status_filter: Optional[JobStatus] = None, age_group_filter: Optional[AgeGroup] = None) -> Dict[str, Any]:
    """Delete multiple jobs based on filters"""

    # Get all job metadata keys
    job_keys = redis_client.keys("job_metadata:*")
    deleted_jobs = []
    failed_jobs = []

    for key in job_keys:
        metadata_data = redis_client.get(key)
        if not metadata_data:
            continue

        try:
            metadata = JobMetadata.model_validate_json(metadata_data)
            job_id = metadata.job_id

            # Apply filters
            should_delete = True

            if status_filter:
                celery_result = AsyncResult(job_id, app=celery_app)
                job_status = _map_celery_status(celery_result.state)
                if job_status != status_filter:
                    should_delete = False

            if age_group_filter:
                request_data = redis_client.get(f"job_request:{job_id}")
                if request_data:
                    request_obj = json.loads(request_data)
                    if request_obj.get("age_group") != age_group_filter.value:
                        should_delete = False

            if should_delete:
                try:
                    await delete_job(job_id)
                    deleted_jobs.append(job_id)
                except Exception as e:
                    failed_jobs.append({"job_id": job_id, "error": str(e)})

        except Exception as e:
            continue

    return {
        "deleted_count": len(deleted_jobs),
        "failed_count": len(failed_jobs),
        "deleted_jobs": deleted_jobs,
        "failed_jobs": failed_jobs if failed_jobs else None
    }


# FastAPI router setup would go here - these functions would be decorated with @router.get, @router.post, etc.
# Example:
# from fastapi import APIRouter
# router = APIRouter(prefix="/api/v1", tags=["jobs"])
#
# @router.get("/calibrate/{job_id}/status", response_model=JobStatusResponse)
# async def get_calibration_status(job_id: str, log_level: Optional[LogLevel] = None):
#     return await get_job_status(job_id, log_level)