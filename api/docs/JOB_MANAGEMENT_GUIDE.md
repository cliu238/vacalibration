# VA-Calibration API - Job Management Guide

This guide covers the comprehensive job management system including async processing, batch operations, result caching, and monitoring.

## Overview

The job management system provides:

- **Asynchronous Processing**: Long-running calibration jobs with progress tracking
- **Batch Processing**: Multiple jobs processed in parallel with intelligent load balancing
- **Result Caching**: Automatic caching with TTL and intelligent cache key generation
- **Comprehensive Monitoring**: Real-time status, logs, and system health
- **Advanced Filtering**: Filter jobs by status, type, country, age group, and date ranges

## Quick Start

### 1. Start Required Services

```bash
# Start Redis (for caching and job storage)
redis-server

# Start Celery worker (for background job processing)
celery -A api.app.job_endpoints worker --loglevel=info --queue=calibration

# Start API server
cd api && python -m uvicorn app.main_direct:app --reload
```

### 2. Create Your First Job

```bash
curl -X POST "http://localhost:8000/api/v1/calibrate/async" \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique",
    "priority": 5,
    "use_cache": true
  }'
```

### 3. Monitor Job Progress

```bash
# Get job status with logs
curl "http://localhost:8000/api/v1/calibrate/{job_id}/status?log_level=info&log_limit=50"

# Get final results
curl "http://localhost:8000/api/v1/calibrate/{job_id}/result"
```

## API Endpoints

### Job Creation and Management

#### Create Async Calibration Job
```
POST /api/v1/calibrate/async
```

**Request Body:**
```json
{
  "va_data": {"insilicova": "use_example"},
  "age_group": "neonate",
  "country": "Mozambique",
  "mmat_type": "prior",
  "ensemble": true,
  "priority": 5,
  "timeout_minutes": 30,
  "use_cache": true
}
```

**Response:**
```json
{
  "job_id": "job_abc123456789",
  "status": "created"
}
```

#### Get Job Status
```
GET /api/v1/calibrate/{job_id}/status
```

**Query Parameters:**
- `log_level`: Filter logs by level (debug, info, warning, error, critical)
- `log_limit`: Maximum log entries to return (1-1000, default: 100)
- `log_offset`: Number of log entries to skip (default: 0)

**Response:**
```json
{
  "job_id": "job_abc123456789",
  "status": "running",
  "progress": {
    "current_step": 3,
    "total_steps": 5,
    "step_name": "Running R calibration",
    "progress_percentage": 60.0,
    "estimated_completion": "2024-01-15T14:30:00Z"
  },
  "metadata": {
    "job_id": "job_abc123456789",
    "job_type": "calibration",
    "created_at": "2024-01-15T14:25:00Z",
    "started_at": "2024-01-15T14:25:30Z",
    "priority": 5
  },
  "logs": [
    {
      "timestamp": "2024-01-15T14:26:00Z",
      "level": "info",
      "message": "Executing R calibration script",
      "component": "r_processor"
    }
  ],
  "result_summary": null,
  "error_details": null
}
```

#### Get Job Results
```
GET /api/v1/calibrate/{job_id}/result
```

**Response:**
```json
{
  "job_id": "job_abc123456789",
  "status": "success",
  "result": {
    "status": "success",
    "uncalibrated": {
      "insilicova": [0.15, 0.25, 0.35, 0.10, 0.05, 0.10]
    },
    "calibrated": {
      "insilicova": {
        "mean": [0.12, 0.28, 0.30, 0.15, 0.08, 0.07],
        "lower_ci": [0.10, 0.25, 0.28, 0.12, 0.06, 0.05],
        "upper_ci": [0.14, 0.31, 0.32, 0.18, 0.10, 0.09]
      }
    },
    "age_group": "neonate",
    "country": "Mozambique",
    "completed_at": "2024-01-15T14:28:45Z"
  },
  "metadata": {...},
  "cache_info": {
    "cached_at": "2024-01-15T14:28:45Z",
    "source_job_id": "job_abc123456789"
  }
}
```

#### Cancel Job
```
DELETE /api/v1/calibrate/{job_id}
```

**Response:**
```json
{
  "job_id": "job_abc123456789",
  "status": "cancelled"
}
```

### Batch Processing

#### Create Batch Jobs
```
POST /api/v1/calibrate/batch
```

**Request Body:**
```json
{
  "jobs": [
    {
      "va_data": {"insilicova": "use_example"},
      "age_group": "neonate",
      "country": "Mozambique",
      "priority": 8
    },
    {
      "va_data": {"insilicova": "use_example"},
      "age_group": "child",
      "country": "Kenya",
      "priority": 7
    }
  ],
  "batch_name": "Multi-country comparison",
  "parallel_limit": 3,
  "fail_fast": false
}
```

**Response:**
```json
{
  "batch_id": "batch_def987654321",
  "job_ids": ["job_abc123456789", "job_ghi987654321"],
  "batch_metadata": {
    "batch_id": "batch_def987654321",
    "batch_name": "Multi-country comparison",
    "total_jobs": 2,
    "created_at": "2024-01-15T14:30:00Z",
    "parallel_limit": 3,
    "fail_fast": false
  }
}
```

#### Get Batch Status
```
GET /api/v1/calibrate/batch/{batch_id}/status
```

**Response:**
```json
{
  "batch_id": "batch_def987654321",
  "total_jobs": 2,
  "completed_jobs": 1,
  "failed_jobs": 0,
  "running_jobs": 1,
  "pending_jobs": 0,
  "batch_status": "running",
  "job_statuses": [
    {"job_id": "job_abc123456789", "status": "success"},
    {"job_id": "job_ghi987654321", "status": "running"}
  ]
}
```

### Job Listing and Filtering

#### List Jobs
```
GET /api/v1/jobs
```

**Query Parameters:**
- `status`: Filter by job status (pending, running, success, failed, cancelled)
- `job_type`: Filter by job type (calibration, batch_calibration)
- `age_group`: Filter by age group (neonate, child)
- `country`: Filter by country name
- `created_after`: Filter jobs created after date (ISO 8601)
- `created_before`: Filter jobs created before date (ISO 8601)
- `page`: Page number (default: 1)
- `page_size`: Jobs per page (1-100, default: 20)

**Examples:**
```bash
# Get all pending jobs
GET /api/v1/jobs?status=pending

# Get neonate calibrations from Kenya
GET /api/v1/jobs?age_group=neonate&country=Kenya

# Get jobs from last 24 hours
GET /api/v1/jobs?created_after=2024-01-14T14:00:00Z

# Paginated results
GET /api/v1/jobs?page=2&page_size=50
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123456789",
      "job_type": "calibration",
      "created_at": "2024-01-15T14:25:00Z",
      "priority": 5
    }
  ],
  "total_count": 25,
  "page": 1,
  "page_size": 20,
  "has_next": true
}
```

### Cache Management

#### Get Cache Statistics
```
GET /api/v1/cache/stats
```

**Response:**
```json
{
  "total_cached_results": 15,
  "cache_hit_rate": 23.5,
  "total_cache_size_mb": 2.34,
  "oldest_cached_result": "2024-01-15T10:00:00Z",
  "newest_cached_result": "2024-01-15T14:28:45Z"
}
```

#### Clear Cache
```
DELETE /api/v1/cache/clear?confirm=true
```

**Query Parameters:**
- `confirm`: Required confirmation flag (must be true)
- `age_group`: Clear cache for specific age group
- `country`: Clear cache for specific country

**Response:**
```json
{
  "cleared_results": 15,
  "message": "Cleared 15 cached results"
}
```

### System Monitoring

#### Get System Health
```
GET /api/v1/jobs/health
```

**Response:**
```json
{
  "status": "healthy",
  "redis": "healthy",
  "celery": "healthy",
  "queue_stats": {
    "pending_jobs": 5,
    "cached_results": 15
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

#### Get Job Metrics
```
GET /api/v1/jobs/metrics?time_range=24h
```

**Response:**
```json
{
  "time_range": "24h",
  "total_jobs": 45,
  "success_rate": 94.4,
  "average_duration_seconds": 127.5,
  "cache_hit_rate": 23.5,
  "error_rate": 5.6
}
```

## Job Statuses

| Status | Description |
|--------|-------------|
| `pending` | Job created and queued for processing |
| `running` | Job is currently being processed |
| `success` | Job completed successfully |
| `failed` | Job failed due to error |
| `cancelled` | Job was cancelled by user |
| `timeout` | Job exceeded timeout limit |

## Log Levels

| Level | Description |
|-------|-------------|
| `debug` | Detailed debugging information |
| `info` | General information about job progress |
| `warning` | Warning messages about potential issues |
| `error` | Error messages for failures |
| `critical` | Critical errors that stop processing |

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional_password

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Job Configuration
CACHE_TTL=3600  # 1 hour
MAX_LOG_ENTRIES=1000
BATCH_MAX_SIZE=50
DEFAULT_TIMEOUT_MINUTES=30
MAX_TIMEOUT_MINUTES=120

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["*"]
```

### Celery Worker Configuration

Start Celery worker with optimal settings:

```bash
celery -A api.app.job_endpoints worker \
  --loglevel=info \
  --concurrency=4 \
  --prefetch-multiplier=1 \
  --max-tasks-per-child=1000 \
  --queue=calibration
```

## Error Handling

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Job/batch not found |
| 500 | Internal Server Error - Processing failure |
| 503 | Service Unavailable - System unhealthy |

### Error Response Format

```json
{
  "detail": "Job job_abc123456789 not found",
  "status_code": 404,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

## Performance Optimization

### Caching Strategy

1. **Automatic Caching**: Results automatically cached based on request parameters
2. **Cache Keys**: Generated from VA data, age group, country, and calibration settings
3. **TTL Management**: Configurable time-to-live for cache entries
4. **Cache Warming**: Frequently used configurations can be pre-cached

### Batch Processing Best Practices

1. **Optimal Batch Size**: 10-25 jobs for best performance
2. **Priority Management**: Use priorities 1-10 to control processing order
3. **Resource Allocation**: Set appropriate parallel limits based on system capacity
4. **Monitoring**: Track batch progress and individual job statuses

### Scaling Considerations

1. **Redis Clustering**: For high-volume deployments
2. **Celery Workers**: Scale horizontally with multiple worker processes
3. **Queue Management**: Use separate queues for different job types
4. **Resource Monitoring**: Monitor CPU, memory, and R process usage

## Troubleshooting

### Common Issues

1. **Jobs Stuck in Pending**
   - Check Celery worker status
   - Verify Redis connectivity
   - Check queue configuration

2. **High Memory Usage**
   - Monitor R process memory consumption
   - Implement job cleanup after completion
   - Use appropriate worker limits

3. **Cache Misses**
   - Verify cache key generation logic
   - Check Redis memory limits
   - Monitor cache TTL settings

### Debugging Commands

```bash
# Check Redis connectivity
redis-cli ping

# Monitor Celery queues
celery -A api.app.job_endpoints inspect active_queues

# View worker status
celery -A api.app.job_endpoints inspect stats

# Monitor job logs
curl "http://localhost:8000/api/v1/calibrate/{job_id}/status?log_level=debug"
```

## Integration Examples

See `api/app/integration_example.py` for comprehensive integration examples including:

- Single job workflow
- Batch processing
- Cache management
- Job filtering and monitoring
- System health checks

## API Client Libraries

### Python Client

```python
from api.app.integration_example import VACalibrationJobClient

client = VACalibrationJobClient("http://localhost:8000")

# Create job
job = await client.create_job({
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique"
})

# Monitor progress
status = await client.get_job_status(job["job_id"])

# Get results
if status["status"] == "success":
    results = await client.get_job_result(job["job_id"])
```

### JavaScript/TypeScript

```typescript
interface CalibrationJob {
  va_data: Record<string, any>;
  age_group: "neonate" | "child";
  country: string;
  priority?: number;
  use_cache?: boolean;
}

class VACalibrationClient {
  constructor(private baseUrl: string) {}

  async createJob(job: CalibrationJob): Promise<{job_id: string}> {
    const response = await fetch(`${this.baseUrl}/api/v1/calibrate/async`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(job)
    });
    return response.json();
  }

  async getJobStatus(jobId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/calibrate/${jobId}/status`);
    return response.json();
  }
}
```

## Security Considerations

1. **Rate Limiting**: Implement rate limiting for job creation
2. **Authentication**: Add authentication for production deployments
3. **Input Validation**: Validate all input parameters
4. **Resource Limits**: Set appropriate timeouts and memory limits
5. **Access Control**: Restrict access to sensitive endpoints

---

For more information, see the main API documentation or contact the development team.