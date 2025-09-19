# VA-Calibration WebSocket API Documentation

## Overview

The VA-Calibration API provides real-time WebSocket endpoints for monitoring calibration jobs with live progress updates, logs, and results. This allows clients to receive instant feedback during long-running calibration processes.

## WebSocket Endpoints

### `/ws/calibrate/{job_id}/logs`

**Description**: Real-time stream of calibration logs, progress updates, and results for a specific job.

**Connection URL**: `ws://localhost:8000/ws/calibrate/{job_id}/logs`

**Parameters**:
- `job_id` (string): The calibration job identifier

**Connection Validation**:
- Job must exist before connecting
- Invalid job IDs will result in connection closure with code 4004

## Message Types

All WebSocket messages follow a consistent JSON format:

```json
{
  "type": "message_type",
  "job_id": "string",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {},
  "sequence": 123
}
```

### 1. Connection Messages

**Type**: `connection`

Sent when a client successfully connects to a job's WebSocket stream.

```json
{
  "type": "connection",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "status": "connected",
    "message": "Connected to job 12345678-1234-1234-1234-123456789abc",
    "server_time": "2024-09-19T12:34:56.789Z"
  },
  "sequence": 1
}
```

### 2. Log Messages

**Type**: `log`

Real-time R script output and system logs.

```json
{
  "type": "log",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "line": "Loading vacalibration package...",
    "level": "info",
    "source": "R_script"
  },
  "sequence": 15
}
```

**Log Levels**:
- `info` - General information
- `warning` - Warning messages
- `error` - Error messages
- `debug` - Debug information

### 3. Progress Messages

**Type**: `progress`

Calibration progress updates with percentage completion.

```json
{
  "type": "progress",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "progress": 45.5,
    "stage": "Running MCMC calibration",
    "percentage": "45.5%"
  },
  "sequence": 25
}
```

### 4. Status Messages

**Type**: `status`

Job status changes and important updates.

```json
{
  "type": "status",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "status": "running",
    "message": "Calibration started successfully",
    "timestamp": "2024-09-19T12:34:56.789Z"
  },
  "sequence": 5
}
```

**Status Values**:
- `pending` - Job queued for execution
- `running` - Job currently executing
- `completed` - Job finished successfully
- `failed` - Job failed with errors
- `cancelled` - Job cancelled by user

### 5. Result Messages

**Type**: `result`

Final calibration results when job completes successfully.

```json
{
  "type": "result",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "results": {
      "uncalibrated": {
        "pneumonia": 0.234,
        "sepsis_meningitis_inf": 0.156,
        "prematurity": 0.445,
        "other": 0.165
      },
      "calibrated": {
        "insilicova": {
          "mean": {
            "pneumonia": 0.278,
            "sepsis_meningitis_inf": 0.134,
            "prematurity": 0.398,
            "other": 0.190
          },
          "lower_ci": {
            "pneumonia": 0.245,
            "sepsis_meningitis_inf": 0.115,
            "prematurity": 0.365,
            "other": 0.156
          },
          "upper_ci": {
            "pneumonia": 0.312,
            "sepsis_meningitis_inf": 0.153,
            "prematurity": 0.431,
            "other": 0.224
          }
        }
      }
    },
    "completed_at": "2024-09-19T12:36:45.123Z"
  },
  "sequence": 150
}
```

### 6. Error Messages

**Type**: `error`

Error messages and exception details.

```json
{
  "type": "error",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "error": "R script execution failed",
    "error_type": "r_script_error",
    "timestamp": "2024-09-19T12:34:56.789Z"
  },
  "sequence": 75
}
```

**Error Types**:
- `general` - General application errors
- `r_script_error` - R script execution errors
- `validation_error` - Input validation errors
- `system_error` - System-level errors

### 7. Heartbeat Messages

**Type**: `heartbeat`

Keep-alive messages sent every 30 seconds to maintain connection.

```json
{
  "type": "heartbeat",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "timestamp": "2024-09-19T12:34:56.789Z",
  "data": {
    "timestamp": "2024-09-19T12:34:56.789Z"
  },
  "sequence": 100
}
```

## REST API Endpoints

### Create Real-time Calibration Job

**POST** `/calibrate/realtime`

Creates a new calibration job with WebSocket support.

```json
{
  "va_data": {"insilicova": "use_example"},
  "age_group": "neonate",
  "country": "Mozambique",
  "mmat_type": "prior",
  "ensemble": true
}
```

**Response**:
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "status": "pending",
  "message": "Real-time calibration job created. Connect to WebSocket: /ws/calibrate/12345678-1234-1234-1234-123456789abc/logs",
  "created_at": "2024-09-19T12:34:56.789Z"
}
```

### Get Job Status

**GET** `/calibrate/{job_id}/status`

Get detailed status of a calibration job.

**Response**:
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "status": "running",
  "progress": 45.5,
  "stage": "Running MCMC calibration",
  "created_at": "2024-09-19T12:34:56.789Z",
  "started_at": "2024-09-19T12:35:00.123Z",
  "completed_at": null,
  "error": null,
  "has_result": false
}
```

### WebSocket Statistics

**GET** `/websocket/stats`

Get WebSocket connection statistics.

**Response**:
```json
{
  "websocket_connections": {
    "total_jobs": 3,
    "total_connections": 5,
    "jobs": {
      "job1": {
        "connections": 2,
        "last_sequence": 45
      },
      "job2": {
        "connections": 3,
        "last_sequence": 78
      }
    }
  },
  "server_time": "2024-09-19T12:34:56.789Z"
}
```

## Client Implementation

### JavaScript Example

```javascript
const jobId = 'your-job-id-here';
const ws = new WebSocket(`ws://localhost:8000/ws/calibrate/${jobId}/logs`);

ws.onopen = () => {
    console.log('Connected to calibration job:', jobId);
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
        case 'connection':
            console.log('✅ Connected:', message.data.message);
            break;

        case 'log':
            console.log(`📝 [${message.data.level}] ${message.data.line}`);
            break;

        case 'progress':
            console.log(`📊 Progress: ${message.data.percentage} - ${message.data.stage}`);
            updateProgressBar(message.data.progress);
            break;

        case 'status':
            console.log(`📋 Status: ${message.data.status} - ${message.data.message}`);
            break;

        case 'result':
            console.log('🎉 Calibration completed!');
            displayResults(message.data.results);
            break;

        case 'error':
            console.error(`❌ Error: ${message.data.error}`);
            break;

        case 'heartbeat':
            console.log('💓 Heartbeat');
            break;
    }
};

ws.onclose = () => {
    console.log('WebSocket connection closed');
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

### Python Example

```python
import asyncio
import json
import websockets

async def monitor_calibration(job_id):
    uri = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"

    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'progress':
                print(f"Progress: {data['data']['percentage']} - {data['data']['stage']}")
            elif data['type'] == 'result':
                print("Calibration completed!")
                print(json.dumps(data['data']['results'], indent=2))
                break
            elif data['type'] == 'error':
                print(f"Error: {data['data']['error']}")
                break

# Usage
asyncio.run(monitor_calibration('your-job-id-here'))
```

## Message Buffering

The WebSocket system includes message buffering for late connections:

- **Buffer Size**: Last 100 messages per job
- **Retention**: Messages kept for 1 hour after job completion
- **Late Connection**: Clients connecting after job start receive buffered messages in chronological order

## Connection Management

### Features

- **Multiple Clients**: Multiple WebSocket clients can connect to the same job
- **Heartbeat**: Automatic heartbeat every 30 seconds
- **Graceful Disconnection**: Proper cleanup on client disconnect
- **Connection Recovery**: Clients can reconnect and receive buffered messages

### Connection Limits

- No explicit limit on connections per job
- Server resources may limit total concurrent connections
- Consider implementing rate limiting for production use

## Error Handling

### Connection Errors

- **4004**: Job not found
- **1000**: Normal closure
- **1006**: Abnormal closure (network issues)

### Message Handling

- Invalid JSON messages are logged but don't terminate connection
- Unknown message types are handled gracefully
- Client should implement reconnection logic for network failures

## Production Considerations

### Redis Configuration

Ensure Redis is properly configured for production:

```bash
# Redis configuration for WebSocket messaging
redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Scaling

- Use Redis Cluster for horizontal scaling
- Configure multiple FastAPI instances with shared Redis
- Implement load balancing for WebSocket connections

### Monitoring

- Monitor WebSocket connection counts
- Track message throughput and latency
- Set up alerts for Redis memory usage

### Security

- Implement authentication for WebSocket connections
- Add rate limiting to prevent abuse
- Use HTTPS/WSS in production
- Validate job ownership before allowing connections

## Testing

Use the provided test client:

```bash
# Test with example data
python tests/websocket_client_example.py

# Monitor existing job
python tests/websocket_client_example.py job-id-here
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check if Redis is running and API server is started
2. **Job Not Found**: Verify job ID exists and is valid
3. **No Messages**: Ensure job is running and Redis pubsub is working
4. **Memory Issues**: Check Redis memory usage and configure limits

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed WebSocket connection and message handling logs.