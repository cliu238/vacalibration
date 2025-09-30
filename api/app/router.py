#!/usr/bin/env python3
"""
FastAPI Router for Job Management Endpoints
Integrates comprehensive job orchestration with the main API
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime

from .job_endpoints import (
    # Request/Response Models
    CalibrationJobRequest,
    BatchCalibrationRequest,
    JobStatusResponse,
    JobListResponse,
    JobResultResponse,
    BatchJobResponse,
    BatchStatusResponse,
    CacheStats,
    JobListFilter,
    JobStatus,
    LogLevel,
    AgeGroup,

    # Core Functions
    get_job_status,
    create_calibration_job,
    create_batch_jobs,
    list_jobs,
    cancel_job,
    get_job_result,
    get_batch_status,
    get_cache_statistics,
    clear_cache,
    delete_job,
    delete_all_jobs
)

# Create router with comprehensive job management
router = APIRouter(
    prefix="/api/v1",
    tags=["Job Management"],
    responses={
        404: {"description": "Job not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)

# Job Status and Monitoring Endpoints
@router.get(
    "/calibrate/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description="Get comprehensive status information for a calibration job including progress, logs, and metadata"
)
async def get_calibration_status(
    job_id: str,
    log_level: Optional[LogLevel] = Query(None, description="Filter logs by level"),
    log_limit: int = Query(100, description="Maximum number of log entries to return", ge=1, le=1000),
    log_offset: int = Query(0, description="Number of log entries to skip for pagination", ge=0)
):
    """
    Get detailed status information for a calibration job.

    **Features:**
    - Real-time job progress tracking
    - Filtered log retrieval with pagination
    - Result summaries for completed jobs
    - Error details for failed jobs
    - Comprehensive metadata

    **Log Levels:** debug, info, warning, error, critical
    """
    try:
        return await get_job_status(job_id, log_level, log_limit, log_offset)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/calibrate/async",
    response_model=dict,
    summary="Create Async Calibration Job",
    description="Create a new asynchronous calibration job with comprehensive configuration options"
)
async def create_async_calibration(
    request: CalibrationJobRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new asynchronous calibration job.

    **Features:**
    - Priority-based job scheduling
    - Configurable timeouts
    - Result caching with TTL
    - Comprehensive logging
    - Progress tracking

    **Returns:** Job ID and creation status
    """
    try:
        return await create_calibration_job(request, background_tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


# Batch Processing Endpoints
@router.post(
    "/calibrate/batch",
    response_model=BatchJobResponse,
    summary="Create Batch Calibration Jobs",
    description="Process multiple calibration requests in parallel with intelligent load balancing"
)
async def create_batch_calibration(request: BatchCalibrationRequest):
    """
    Create and process multiple calibration jobs in parallel.

    **Features:**
    - Parallel processing with configurable limits
    - Fail-fast option for early termination
    - Batch progress tracking
    - Individual job monitoring
    - Resource optimization

    **Limits:**
    - Maximum 50 jobs per batch
    - Configurable parallel execution limit
    - Intelligent queuing and load balancing
    """
    try:
        return await create_batch_jobs(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create batch: {str(e)}")


@router.get(
    "/calibrate/batch/{batch_id}/status",
    response_model=BatchStatusResponse,
    summary="Get Batch Status",
    description="Get comprehensive status information for batch job processing"
)
async def get_batch_processing_status(batch_id: str):
    """
    Get detailed status for batch job processing.

    **Features:**
    - Overall batch progress
    - Individual job statuses
    - Success/failure counts
    - Batch completion estimation
    - Error aggregation
    """
    try:
        return await get_batch_status(batch_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        raise HTTPException(status_code=500, detail=str(e))


# Job Management Endpoints
@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List Jobs",
    description="List calibration jobs with comprehensive filtering and pagination"
)
async def list_calibration_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    age_group: Optional[AgeGroup] = Query(None, description="Filter by age group"),
    country: Optional[str] = Query(None, description="Filter by country"),
    created_after: Optional[datetime] = Query(None, description="Filter jobs created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter jobs created before this date"),
    page: int = Query(1, description="Page number for pagination", ge=1),
    page_size: int = Query(20, description="Number of jobs per page", ge=1, le=100)
):
    """
    List calibration jobs with advanced filtering and pagination.

    **Filtering Options:**
    - Job status (pending, running, success, failed, cancelled)
    - Job type (calibration, batch_calibration)
    - Age group (neonate, child)
    - Country name
    - Creation date range

    **Features:**
    - Efficient pagination
    - Real-time status updates
    - Comprehensive metadata
    - Total count tracking
    """
    try:
        filters = JobListFilter(
            status=status,
            job_type=job_type,
            age_group=age_group,
            country=country,
            created_after=created_after,
            created_before=created_before
        )
        return await list_jobs(filters, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.delete(
    "/calibrate/{job_id}",
    summary="Cancel Job",
    description="Cancel a running calibration job and clean up resources"
)
async def cancel_calibration_job(job_id: str):
    """
    Cancel a running calibration job.

    **Features:**
    - Immediate task termination
    - Resource cleanup
    - Status update logging
    - Graceful shutdown handling

    **Note:** Cancelled jobs cannot be resumed
    """
    try:
        return await cancel_job(job_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get(
    "/calibrate/{job_id}/result",
    response_model=JobResultResponse,
    summary="Get Job Results",
    description="Retrieve final calibration results for completed jobs"
)
async def get_calibration_result(job_id: str):
    """
    Get final calibration results for a completed job.

    **Features:**
    - Complete calibration results
    - Uncalibrated vs calibrated CSMFs
    - Confidence intervals
    - Cache information
    - Result metadata

    **Requirements:** Job must be in SUCCESS or FAILED status
    """
    try:
        return await get_job_result(job_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Job or results not found for {job_id}")
        if "not completed" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


# Cache Management Endpoints
@router.get(
    "/cache/stats",
    response_model=CacheStats,
    summary="Get Cache Statistics",
    description="Get comprehensive statistics about result caching system"
)
async def get_caching_statistics():
    """
    Get detailed statistics about the result caching system.

    **Metrics:**
    - Total cached results
    - Cache hit rate
    - Total cache size
    - Cache age distribution
    - Performance metrics
    """
    try:
        return await get_cache_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete(
    "/cache/clear",
    summary="Clear Cache",
    description="Clear cached results with optional filtering"
)
async def clear_result_cache(
    age_group: Optional[AgeGroup] = Query(None, description="Clear cache for specific age group"),
    country: Optional[str] = Query(None, description="Clear cache for specific country"),
    confirm: bool = Query(False, description="Confirmation flag required for cache clearing")
):
    """
    Clear cached calibration results.

    **Features:**
    - Selective clearing by age group or country
    - Confirmation requirement for safety
    - Detailed clearing statistics
    - Immediate cache invalidation

    **Warning:** This action cannot be undone
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Cache clearing requires explicit confirmation (set confirm=true)"
        )

    try:
        return await clear_cache(age_group, country)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# Health and Monitoring Endpoints
@router.get(
    "/jobs/health",
    summary="Job System Health",
    description="Get health status of the job processing system"
)
async def get_job_system_health():
    """
    Get comprehensive health status of the job processing system.

    **Checks:**
    - Redis connectivity
    - Celery worker status
    - Queue lengths
    - Error rates
    - Performance metrics
    """
    try:
        from .job_endpoints import redis_client, celery_app

        # Check Redis connectivity
        redis_status = "healthy"
        try:
            redis_client.ping()
        except Exception:
            redis_status = "unhealthy"

        # Check Celery status
        celery_status = "healthy"
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            if not active_workers:
                celery_status = "no_workers"
        except Exception:
            celery_status = "unhealthy"

        # Get queue statistics
        try:
            queue_stats = {
                "pending_jobs": len(redis_client.keys("job_metadata:*")),
                "cached_results": len(redis_client.keys("calibration_result:*"))
            }
        except Exception:
            queue_stats = {"error": "Unable to get queue stats"}

        return {
            "status": "healthy" if redis_status == "healthy" and celery_status == "healthy" else "degraded",
            "redis": redis_status,
            "celery": celery_status,
            "queue_stats": queue_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Advanced Endpoints
@router.get(
    "/jobs/metrics",
    summary="Job Metrics",
    description="Get detailed metrics about job processing performance"
)
async def get_job_metrics(
    time_range: str = Query("24h", description="Time range for metrics (1h, 24h, 7d, 30d)")
):
    """
    Get detailed performance metrics for job processing.

    **Metrics:**
    - Job completion rates
    - Average processing times
    - Error rates by type
    - Cache hit rates
    - Resource utilization

    **Time Ranges:** 1h, 24h, 7d, 30d
    """
    try:
        # This would be implemented with proper metrics collection
        # For now, return basic structure
        return {
            "time_range": time_range,
            "total_jobs": 0,
            "success_rate": 0.0,
            "average_duration_seconds": 0.0,
            "cache_hit_rate": 0.0,
            "error_rate": 0.0,
            "note": "Detailed metrics collection not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post(
    "/jobs/retry/{job_id}",
    summary="Retry Failed Job",
    description="Retry a failed calibration job with optional parameter modifications"
)
async def retry_failed_job(
    job_id: str,
    modify_params: bool = Query(False, description="Allow parameter modifications"),
    new_priority: Optional[int] = Query(None, description="New job priority (1-10)", ge=1, le=10),
    new_timeout: Optional[int] = Query(None, description="New timeout in minutes", ge=1, le=120)
):
    """
    Retry a failed calibration job.

    **Features:**
    - Automatic parameter recovery
    - Optional parameter modifications
    - Retry count tracking
    - Failure analysis
    - Intelligent backoff

    **Requirements:** Original job must be in FAILED status
    """
    try:
        # Implementation would involve:
        # 1. Get original job metadata and parameters
        # 2. Check if job is in FAILED status
        # 3. Create new job with same or modified parameters
        # 4. Track retry relationship

        return {
            "message": "Job retry functionality not yet implemented",
            "original_job_id": job_id,
            "retry_requested": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")


# Job Deletion Endpoints
@router.delete(
    "/jobs/{job_id}",
    summary="Delete Job",
    description="Delete a job and all its associated data from Redis"
)
async def delete_job_endpoint(job_id: str):
    """
    Delete a job and all its associated data.

    **Features:**
    - Terminates running jobs
    - Removes all Redis keys (metadata, logs, results)
    - Cannot be undone

    **Warning:** This action permanently deletes the job
    """
    try:
        return await delete_job(job_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")


@router.delete(
    "/jobs/clear/all",
    summary="Delete All Jobs",
    description="Delete multiple jobs with optional filtering"
)
async def delete_all_jobs_endpoint(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    age_group: Optional[AgeGroup] = Query(None, description="Filter by age group"),
    confirm: bool = Query(False, description="Confirmation flag required for deletion")
):
    """
    Delete all jobs matching the specified filters.

    **Features:**
    - Optional filtering by status and age group
    - Bulk deletion with progress tracking
    - Confirmation requirement for safety

    **Warning:** This action cannot be undone
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Job deletion requires explicit confirmation (set confirm=true)"
        )

    try:
        return await delete_all_jobs(status, age_group)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete jobs: {str(e)}")


# Export router for integration with main FastAPI app
__all__ = ["router"]