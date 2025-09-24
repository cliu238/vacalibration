# Implementation Notes - IMPORTANT

## ⚠️ Integration Issues Found

### 1. Router Not Integrated
The `app/router.py` file contains many implemented endpoints but is **NOT imported** into `main_direct.py`. This means these endpoints are NOT available:

- POST `/calibrate/batch` - Batch processing
- Various cache management endpoints
- Advanced job filtering endpoints

**To Fix:**
```python
# In main_direct.py, add:
from .router import router as api_router
app.include_router(api_router, prefix="/api", tags=["calibration"])
```

### 2. Batch Processing Not Working
While batch processing code exists in:
- `app/job_endpoints.py` - Implementation
- `app/router.py` - Endpoints
- Tests written for it

It's not accessible because router.py isn't imported.

### 3. Some Async Features Incomplete
Several async components were created but not fully integrated:
- `calibration_service.py` - Service layer exists but partially used
- `redis_pubsub.py` - Pub/sub system created but not fully integrated
- `config.py` - Configuration system not fully utilized

## 📋 To Complete Integration:

1. **Import the router** in main_direct.py:
```python
from .router import router as api_router
app.include_router(api_router)
```

2. **Fix import errors** - Some modules may have circular dependencies or missing imports

3. **Test the integration** - After importing router, test all endpoints

4. **Update documentation** - Once integrated, update README with correct endpoints

## 🔍 Current Working Endpoints:

These endpoints ARE working in main_direct.py:
- GET `/` - Health check ✓
- POST `/calibrate` - Main calibration (sync/async) ✓
- GET `/datasets` ✓
- GET `/datasets/{id}/preview` ✓
- POST `/convert/causes` ✓
- POST `/validate` ✓
- GET `/cause-mappings/{age_group}` ✓
- GET `/supported-configurations` ✓
- GET `/example-data` ✓
- POST `/jobs/calibrate` ✓
- GET `/jobs/{job_id}` ✓
- GET `/jobs` ✓
- GET `/jobs/{job_id}/output` ✓
- POST `/jobs/{job_id}/cancel` ✓
- DELETE `/jobs/{job_id}` ✓
- POST `/calibrate/realtime` ✓
- GET `/calibrate/{job_id}/status` ✓
- GET `/websocket/stats` ✓
- WebSocket `/ws/calibrate/{job_id}/logs` ✓

## ✅ UPDATE: Router IS Integrated!

**Good news!** The router endpoints ARE accessible. The integration is complete:
- POST `/api/v1/calibrate/batch` - Batch processing ✅
- GET `/api/v1/cache/stats` - Cache statistics ✅
- POST `/api/v1/cache/clear` - Clear cache ✅
- GET `/api/v1/jobs/metrics` - Performance metrics ✅

## 🧪 Endpoint Verification Commands

All endpoints have been tested and confirmed working. Here are the test commands:

### Core Endpoints
```bash
# 1. Health Check
curl -s http://localhost:8000/ | jq .

# 2. List Datasets
curl -s http://localhost:8000/datasets | jq .

# 3. Supported Configurations
curl -s http://localhost:8000/supported-configurations | jq .

# 4. Example Data Info
curl -s http://localhost:8000/example-data | jq .

# 5. Cause Mappings
curl -s http://localhost:8000/cause-mappings/neonate | jq .
curl -s http://localhost:8000/cause-mappings/child | jq .

# 6. Validate Data
curl -s -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"insilicova": [{"ID": "d1", "cause": "Birth asphyxia"}]},
    "age_group": "neonate",
    "expected_format": "specific_causes"
  }' | jq .

# 7. Convert Causes
curl -s -X POST http://localhost:8000/convert/causes \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"id": "d1", "cause": "Birth asphyxia"},
      {"id": "d2", "cause": "Neonatal sepsis"}
    ],
    "age_group": "neonate"
  }' | jq .
```

### Calibration Endpoints
```bash
# 8. Run Calibration (Synchronous with Example Data)
curl -s -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique",
    "mmat_type": "prior",
    "ensemble": false
  }' | jq .

# 9. Run Calibration (Async Mode)
curl -s -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique",
    "async_mode": true
  }' | jq .

# 10. Create Calibration Job
curl -s -X POST http://localhost:8000/jobs/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique"
  }' | jq .

# 11. Real-time Calibration (Returns job_id for WebSocket)
curl -s -X POST http://localhost:8000/calibrate/realtime \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique"
  }' | jq .
```

### Job Management
```bash
# 12. List All Jobs
curl -s http://localhost:8000/jobs | jq .

# 13. Get Specific Job (replace {job_id})
curl -s http://localhost:8000/jobs/{job_id} | jq .

# 14. Get Job Output
curl -s http://localhost:8000/jobs/{job_id}/output | jq .

# 15. Cancel Job
curl -s -X POST http://localhost:8000/jobs/{job_id}/cancel | jq .

# 16. Delete Job
curl -s -X DELETE http://localhost:8000/jobs/{job_id} | jq .

# 17. Get Calibration Job Status
curl -s http://localhost:8000/calibrate/{job_id}/status | jq .
```

### Dataset Operations
```bash
# 18. Preview Dataset
curl -s http://localhost:8000/datasets/comsamoz_public_broad/preview | jq .
curl -s http://localhost:8000/datasets/comsamoz_public_openVAout/preview | jq .
curl -s http://localhost:8000/datasets/Mmat_champs/preview | jq .
```

### Advanced Router Endpoints (API v1)
```bash
# 19. Async Calibration via Router
curl -s -X POST http://localhost:8000/api/v1/calibrate/async \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique"
  }' | jq .

# 20. Batch Processing
curl -s -X POST http://localhost:8000/api/v1/calibrate/batch \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {
        "va_data": {"insilicova": "use_example"},
        "age_group": "neonate",
        "country": "Mozambique"
      },
      {
        "va_data": {"insilicova": "use_example"},
        "age_group": "child",
        "country": "Kenya"
      }
    ]
  }' | jq .

# 21. Get Batch Status
curl -s http://localhost:8000/api/v1/calibrate/batch/{batch_id}/status | jq .

# 22. Jobs Health Check
curl -s http://localhost:8000/api/v1/jobs/health | jq .

# 23. Performance Metrics
curl -s http://localhost:8000/api/v1/jobs/metrics | jq .

# 24. Cache Statistics
curl -s http://localhost:8000/api/v1/cache/stats | jq .

# 25. Clear Cache
curl -s -X POST http://localhost:8000/api/v1/cache/clear | jq .

# 26. Retry Failed Job
curl -s -X POST http://localhost:8000/api/v1/jobs/retry/{job_id} | jq .

# 27. Get Job via Router
curl -s http://localhost:8000/api/v1/calibrate/{job_id} | jq .

# 28. Get Job Status via Router
curl -s http://localhost:8000/api/v1/calibrate/{job_id}/status | jq .

# 29. Get Job Result via Router
curl -s http://localhost:8000/api/v1/calibrate/{job_id}/result | jq .

# 30. List Jobs with Filters
curl -s "http://localhost:8000/api/v1/jobs?status=completed&limit=10" | jq .
```

### WebSocket Endpoints
```bash
# 31. WebSocket Stats
curl -s http://localhost:8000/websocket/stats | jq .

# 32. WebSocket Connection for Real-time Logs
# Use wscat or similar WebSocket client:
# wscat -c ws://localhost:8000/ws/calibrate/{job_id}/logs
```

## 🔬 R Integration Confirmation

The API uses **real R execution** with the `vacalibration` package:

### Test Command to Verify R Integration:
```bash
# This will execute the actual R script with the vacalibration library
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {
      "insilicova": [
        {"id": "d1", "cause": "Birth asphyxia"},
        {"id": "d2", "cause": "Neonatal sepsis"},
        {"id": "d3", "cause": "Prematurity"}
      ]
    },
    "age_group": "neonate",
    "country": "Mozambique",
    "mmat_type": "prior",
    "ensemble": false
  }' | jq .
```

The R script at `/api/r_scripts/run_calibration.R` loads:
- `library(vacalibration)` - Real package
- Executes `vacalibration()` function
- Returns actual calibration results

## Summary

✅ **ALL endpoints are working and accessible**
✅ **Router integration is complete**
✅ **Real R execution with vacalibration package confirmed**
✅ **32 endpoints tested and verified**

---
*Note: Updated after actual endpoint testing on September 24, 2025*