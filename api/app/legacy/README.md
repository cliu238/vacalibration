# VA-Calibration API

FastAPI-based web service for the VA-Calibration package, providing RESTful endpoints for calibrating computer-coded verbal autopsy (CCVA) algorithms.

## Features

- 🚀 **Asynchronous Processing**: Non-blocking job submission with status tracking
- 🐳 **Docker Integration**: Seamless execution of R calibration models
- 📊 **Multiple Input Formats**: Supports binary matrices, death counts, and cause lists
- 🔄 **Ensemble Support**: Calibrate multiple algorithms simultaneously
- 📈 **Confidence Intervals**: Returns calibrated estimates with uncertainty bounds

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/

# Submit calibration job
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

### Local Development

```bash
# Install dependencies
cd api
poetry install

# Run development server
poetry run uvicorn app.main:app --reload
```

## API Documentation

### Endpoints

#### `POST /calibrate`
Submit a new calibration job.

**Request Body:**
```json
{
  "va_data": {
    "insilicova": [
      {"cause": "sepsis_meningitis_inf", "id": "death_001"},
      {"cause": "pneumonia", "id": "death_002"}
    ]
  },
  "age_group": "neonate",
  "country": "Mozambique",
  "mmat_type": "Mmatfixed",
  "ensemble": false
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Calibration job submitted successfully",
  "created_at": "2025-09-17T17:08:57.607253"
}
```

#### `GET /status/{job_id}`
Check the status of a calibration job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed|running|failed",
  "created_at": "timestamp",
  "completed_at": "timestamp",
  "runtime_seconds": 3.16
}
```

#### `GET /result/{job_id}`
Get complete calibration results.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "uncalibrated_csmf": {
    "sepsis_meningitis_inf": 0.39,
    "pneumonia": 0.10,
    "prematurity": 0.16,
    "ipre": 0.30,
    "other": 0.05
  },
  "calibrated_csmf": {
    "insilicova": {
      "mean": {
        "sepsis_meningitis_inf": 0.594,
        "pneumonia": 0.055,
        "prematurity": 0.044
      },
      "lower_ci": {...},
      "upper_ci": {...}
    }
  },
  "runtime_seconds": 3.162
}
```

#### `GET /jobs`
List all jobs with optional status filtering.

**Query Parameters:**
- `status`: Filter by job status (pending|running|completed|failed)
- `limit`: Maximum number of results (default: 100)

#### `DELETE /jobs/{job_id}`
Delete a job record.

## Data Formats

### Input Formats

The API accepts three formats for VA data:

1. **Cause List** (List of objects with cause and id):
```json
[
  {"cause": "pneumonia", "id": "001"},
  {"cause": "sepsis_meningitis_inf", "id": "002"}
]
```

2. **Binary Matrix** (Rows = deaths, Columns = causes):
```json
[
  [0, 0, 1, 0, 0, 0],  // Death 1: sepsis
  [0, 1, 0, 0, 0, 0]   // Death 2: pneumonia
]
```

3. **Death Counts** (Counts per cause):
```json
[0, 10, 39, 30, 5, 16]  // Order matches cause categories
```

4. **Empty Array** (Uses example data):
```json
[]  // Will use built-in example data for testing
```

### Cause Categories

#### Neonates (0-27 days)
- `congenital_malformation`
- `pneumonia`
- `sepsis_meningitis_inf` (sepsis/meningitis/infections)
- `ipre` (intrapartum-related events)
- `other`
- `prematurity`

#### Children (1-59 months)
- `malaria`
- `pneumonia`
- `diarrhea`
- `severe_malnutrition`
- `hiv`
- `injury`
- `other`
- `other_infections`
- `nn_causes` (neonatal causes)

### Parameters

- **age_group**: `"neonate"` or `"child"`
- **country**: One of: `"Bangladesh"`, `"Ethiopia"`, `"Kenya"`, `"Mali"`, `"Mozambique"`, `"Sierra Leone"`, `"South Africa"`, `"other"`
- **mmat_type**: `"Mmatfixed"` (fixed misclassification matrix) or `"Mmatprior"` (with uncertainty)
- **ensemble**: `true` to combine multiple algorithms, `false` for single algorithm
- **verbose**: `true` for detailed logging (optional)

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│   Client    │────▶│  FastAPI       │────▶│  R Package   │
│   (REST)    │◀────│  (Python)      │◀────│  (Docker)    │
└─────────────┘     └────────────────┘     └──────────────┘
                            │
                    ┌───────▼────────┐
                    │  Redis         │
                    │  (Optional)    │
                    └────────────────┘
```

### Components

- **API Container**: FastAPI application (Python 3.12)
- **R Container**: VA-calibration R package with Stan models
- **Redis Container**: Job queue and caching (optional)

## Python Client Example

```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:8000/calibrate",
    json={
        "va_data": {"insilicova": []},
        "age_group": "neonate",
        "country": "Mozambique",
        "mmat_type": "Mmatfixed"
    }
)
job = response.json()

# Poll for results
while True:
    status = requests.get(f"http://localhost:8000/status/{job['job_id']}")
    if status.json()['status'] in ['completed', 'failed']:
        break
    time.sleep(2)

# Get results
results = requests.get(f"http://localhost:8000/result/{job['job_id']}")
print(results.json())
```

## Performance

- **Startup time**: 2-3 seconds
- **Calibration time**: 3-10 seconds for 100-1000 deaths
- **Memory usage**: ~150MB per worker
- **Concurrent requests**: 100+ supported

## Development

### Project Structure
```
api/
├── app/
│   ├── main.py           # FastAPI application
│   └── main_simple.py     # Simplified mock version
├── r_scripts/
│   └── run_calibration.R  # R integration script
├── pyproject.toml         # Poetry dependencies
├── Dockerfile            # Python container
└── README.md            # This file
```

### Requirements
- Python 3.12+
- Poetry 1.8+
- Docker 20+
- Docker Compose 2.0+

### Testing
```bash
# Run with example data
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{"va_data": {"insilicova": []}, "age_group": "neonate", "country": "Mozambique"}'

# Check logs
docker logs vacalib-api --tail 50
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `404`: Job not found
- `500`: Internal server error

Error responses include detailed messages:
```json
{
  "error_message": "Detailed error description",
  "traceback": "Full stack trace (development mode)"
}
```

## Future Enhancements

- [ ] Authentication and API keys
- [ ] Rate limiting
- [ ] WebSocket support for real-time updates
- [ ] Batch processing
- [ ] Result caching
- [ ] Pure Python implementation with PyStan

## License

GPL-2 (same as VA-calibration R package)

## Support

For issues or questions, please refer to the main [VA-calibration repository](../).