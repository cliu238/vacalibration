# VA-Calibration API Test Design

## Overview
This document provides a comprehensive test design for the VA-Calibration API, covering all endpoints (implemented and planned), test scenarios, test data management, and test infrastructure requirements.

## Test Framework & Tools

### Primary Testing Stack
- **Framework**: pytest (Python testing framework)
- **API Testing**: pytest + httpx/requests for HTTP testing
- **WebSocket Testing**: pytest-asyncio + websockets
- **Mocking**: pytest-mock for mocking R script execution
- **Coverage**: pytest-cov for code coverage reports
- **Performance**: locust for load testing
- **Security**: OWASP ZAP for security testing

### Test Environment Setup
```bash
# Install test dependencies
poetry add --group dev pytest pytest-asyncio pytest-mock pytest-cov httpx websockets locust

# Run tests
poetry run pytest tests/ -v --cov=app --cov-report=html

# Run specific test categories
poetry run pytest tests/unit -v
poetry run pytest tests/integration -v
poetry run pytest tests/performance -v
```

## Test Categories

### 1. Unit Tests

#### 1.1 Health Check Endpoint Tests (`GET /`)

**Test ID**: UT-001
**Endpoint**: `GET /`
**Implementation Status**: ✅ Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-001-01 | Health check with R available | Status 200, R status "ready" |
| UT-001-02 | Health check with R unavailable | Status 200, R status shows error |
| UT-001-03 | Check data files availability | Status 200, data_files status shown |
| UT-001-04 | Response time < 100ms | Performance baseline met |

```python
# tests/unit/test_health_check.py
import pytest
from httpx import AsyncClient
from app.main_direct import app

@pytest.mark.asyncio
async def test_health_check_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "r_status" in response.json()

@pytest.mark.asyncio
async def test_health_check_data_files():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        data = response.json()
        assert "data_files" in data
        assert "comsamoz_broad" in data["data_files"]
        assert "comsamoz_openVA" in data["data_files"]
```

#### 1.2 Calibration Endpoint Tests (`POST /calibrate`)

**Test ID**: UT-002
**Endpoint**: `POST /calibrate`
**Implementation Status**: ✅ Implemented (sync), ⏳ Planned (async)

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-002-01 | Calibrate with example data | Success with calibrated results |
| UT-002-02 | Calibrate with custom specific causes | Success with mapped broad causes |
| UT-002-03 | Calibrate with binary matrix | Success with direct processing |
| UT-002-04 | Calibrate with death counts | Success with aggregated results |
| UT-002-05 | Invalid age group | 422 Validation Error |
| UT-002-06 | Invalid country | Uses "other" calibration matrix |
| UT-002-07 | Missing required fields | 422 Validation Error |
| UT-002-08 | Malformed JSON | 422 Validation Error |
| UT-002-09 | Empty va_data | Uses example data |
| UT-002-10 | Ensemble calibration | Multiple algorithm results |
| UT-002-11 | Async mode request | Returns job_id and WebSocket URL |
| UT-002-12 | Custom MCMC parameters | Uses specified iterations |
| UT-002-13 | R script timeout | 504 Gateway Timeout |
| UT-002-14 | R script error | 500 with error details |

```python
# tests/unit/test_calibrate.py
import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_calibrate_with_example_data():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/calibrate", json={
            "age_group": "neonate",
            "country": "Mozambique"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "uncalibrated" in data
        assert "calibrated" in data

@pytest.mark.asyncio
async def test_calibrate_with_custom_data():
    test_data = {
        "va_data": {
            "insilicova": [
                {"ID": "d1", "cause": "Birth asphyxia"},
                {"ID": "d2", "cause": "Neonatal sepsis"}
            ]
        },
        "data_format": "specific_causes",
        "age_group": "neonate",
        "country": "Mozambique"
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/calibrate", json=test_data)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_calibrate_validation_error():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/calibrate", json={
            "age_group": "invalid_age_group"
        })
        assert response.status_code == 422
```

#### 1.3 Example Data Endpoint Tests (`GET /example-data`)

**Test ID**: UT-003
**Endpoint**: `GET /example-data`
**Implementation Status**: ✅ Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-003-01 | Get example data info | Returns data structure info |
| UT-003-02 | Verify data format | Correct format specification |
| UT-003-03 | Check sample size | Returns correct counts |

#### 1.4 Datasets Endpoint Tests (`GET /datasets`)

**Test ID**: UT-004
**Endpoint**: `GET /datasets`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-004-01 | List all datasets | Returns array of datasets |
| UT-004-02 | Dataset metadata present | Each has id, name, description |
| UT-004-03 | Filter by age group | Only matching datasets returned |
| UT-004-04 | Filter by format | Only matching formats returned |

#### 1.5 Dataset Preview Tests (`GET /datasets/{dataset_id}/preview`)

**Test ID**: UT-005
**Endpoint**: `GET /datasets/{dataset_id}/preview`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-005-01 | Preview valid dataset | Returns sample records |
| UT-005-02 | Preview invalid dataset | 404 Not Found |
| UT-005-03 | Sample size limit | Max 10 records returned |
| UT-005-04 | Statistics included | Cause distribution present |

#### 1.6 Convert Causes Tests (`POST /convert/causes`)

**Test ID**: UT-006
**Endpoint**: `POST /convert/causes`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-006-01 | Convert neonate causes | Correct broad mappings |
| UT-006-02 | Convert child causes | Correct broad mappings |
| UT-006-03 | Unknown cause handling | Maps to "other" |
| UT-006-04 | Empty data | 400 Bad Request |
| UT-006-05 | Mixed age groups | 400 Bad Request |

#### 1.7 Validate Data Tests (`POST /validate`)

**Test ID**: UT-007
**Endpoint**: `POST /validate`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-007-01 | Validate specific causes | Valid with summary |
| UT-007-02 | Validate binary matrix | Valid with dimensions |
| UT-007-03 | Validate death counts | Valid with total |
| UT-007-04 | Invalid format | Errors with details |
| UT-007-05 | Missing IDs | Warning in response |

#### 1.8 Cause Mappings Tests (`GET /cause-mappings/{age_group}`)

**Test ID**: UT-008
**Endpoint**: `GET /cause-mappings/{age_group}`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-008-01 | Get neonate mappings | Complete mapping dict |
| UT-008-02 | Get child mappings | Complete mapping dict |
| UT-008-03 | Invalid age group | 404 Not Found |

#### 1.9 Supported Configurations Tests (`GET /supported-configurations`)

**Test ID**: UT-009
**Endpoint**: `GET /supported-configurations`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-009-01 | Get all configurations | Complete config object |
| UT-009-02 | Countries list present | All supported countries |
| UT-009-03 | Algorithms list present | All supported algorithms |
| UT-009-04 | Age groups list present | All age groups |

#### 1.10 Job Status Tests (`GET /calibrate/{job_id}/status`)

**Test ID**: UT-010
**Endpoint**: `GET /calibrate/{job_id}/status`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-010-01 | Get running job status | Status "running" with progress |
| UT-010-02 | Get completed job status | Status "completed" with results |
| UT-010-03 | Get failed job status | Status "failed" with error |
| UT-010-04 | Invalid job ID | 404 Not Found |
| UT-010-05 | Logs included | Array of log entries |

#### 1.11 WebSocket Tests (`WebSocket /calibrate/{job_id}/logs`)

**Test ID**: UT-011
**Endpoint**: `WebSocket /calibrate/{job_id}/logs`
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| UT-011-01 | Connect to valid job | Connection established |
| UT-011-02 | Receive log messages | Real-time log streaming |
| UT-011-03 | Receive progress updates | Progress percentage |
| UT-011-04 | Connection closes on complete | Auto-close on finish |
| UT-011-05 | Invalid job ID | Connection refused |
| UT-011-06 | Client disconnect handling | Graceful cleanup |

```python
# tests/unit/test_websocket.py
import pytest
import websockets
import json

@pytest.mark.asyncio
async def test_websocket_connection():
    uri = "ws://localhost:8000/calibrate/test_job_123/logs"
    async with websockets.connect(uri) as websocket:
        # Send subscription message
        await websocket.send(json.dumps({"type": "subscribe"}))

        # Receive log message
        message = await websocket.recv()
        data = json.loads(message)
        assert data["type"] in ["log", "progress", "status"]
```

### 2. Integration Tests

#### 2.1 End-to-End Calibration Workflow

**Test ID**: IT-001
**Description**: Complete calibration workflow from data submission to results

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| IT-001-01 | Submit → Process → Results (sync) | Complete workflow success |
| IT-001-02 | Submit → Job ID → Status → Results (async) | Async workflow success |
| IT-001-03 | Multiple algorithms ensemble | Combined results |
| IT-001-04 | Data validation → Conversion → Calibration | Multi-step workflow |

```python
# tests/integration/test_calibration_workflow.py
@pytest.mark.integration
async def test_complete_calibration_workflow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Validate data
        validate_response = await client.post("/validate", json={
            "data": test_data,
            "format": "specific_causes",
            "age_group": "neonate"
        })
        assert validate_response.json()["valid"] == True

        # Step 2: Convert causes
        convert_response = await client.post("/convert/causes", json={
            "data": test_data,
            "age_group": "neonate"
        })
        broad_causes = convert_response.json()["matrix_format"]

        # Step 3: Calibrate
        calibrate_response = await client.post("/calibrate", json={
            "va_data": {"insilicova": broad_causes},
            "data_format": "broad_causes",
            "age_group": "neonate",
            "country": "Mozambique"
        })
        assert calibrate_response.status_code == 200
```

#### 2.2 Error Recovery Scenarios

**Test ID**: IT-002
**Description**: Test error handling and recovery

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| IT-002-01 | R script failure recovery | Graceful error message |
| IT-002-02 | Timeout and retry | Retry mechanism works |
| IT-002-03 | Partial data processing | Handles incomplete data |
| IT-002-04 | Connection loss recovery | Reconnect capability |

#### 2.3 Data Format Compatibility

**Test ID**: IT-003
**Description**: Test all data format conversions

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| IT-003-01 | Specific → Broad → Calibrate | Format chain works |
| IT-003-02 | Death counts → Calibrate | Direct processing |
| IT-003-03 | Mixed format ensemble | Handles multiple formats |

### 3. Performance Tests

#### 3.1 Load Testing

**Test ID**: PT-001
**Tool**: Locust

| Test Case | Description | Target | Threshold |
|-----------|-------------|--------|-----------|
| PT-001-01 | Single user response time | GET / | < 100ms |
| PT-001-02 | Calibration response time (small) | < 100 deaths | < 5s |
| PT-001-03 | Calibration response time (medium) | 1000-5000 deaths | < 30s |
| PT-001-04 | Calibration response time (large) | > 5000 deaths | < 60s |
| PT-001-05 | Concurrent users | 100 users | No errors |
| PT-001-06 | Requests per second | Health check | > 100 RPS |
| PT-001-07 | Memory usage | During calibration | < 1GB |
| PT-001-08 | CPU usage | During calibration | < 80% |

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task(10)
    def health_check(self):
        self.client.get("/")

    @task(5)
    def get_example_data(self):
        self.client.get("/example-data")

    @task(1)
    def calibrate_small(self):
        self.client.post("/calibrate", json={
            "age_group": "neonate",
            "country": "Mozambique"
        })
```

#### 3.2 Stress Testing

**Test ID**: PT-002
**Description**: System behavior under extreme load

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| PT-002-01 | 500 concurrent calibrations | Queuing works |
| PT-002-02 | Large dataset (10K deaths) | Completes < 2min |
| PT-002-03 | Memory leak detection | No memory growth |
| PT-002-04 | R process management | Proper cleanup |

#### 3.3 Scalability Testing

**Test ID**: PT-003
**Description**: Horizontal scaling verification

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| PT-003-01 | Multi-instance load balancing | Even distribution |
| PT-003-02 | Session affinity (WebSocket) | Sticky sessions work |
| PT-003-03 | Cache hit ratio | > 80% for samples |

### 4. Security Tests

#### 4.1 Input Validation Security

**Test ID**: ST-001
**Tool**: Manual + OWASP ZAP

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| ST-001-01 | SQL injection attempts | Properly escaped |
| ST-001-02 | Command injection in R | Sandboxed execution |
| ST-001-03 | Path traversal attempts | Blocked |
| ST-001-04 | XXE injection | XML parsing disabled |
| ST-001-05 | JSON bomb | Size limits enforced |
| ST-001-06 | Unicode exploits | Proper encoding |

```python
# tests/security/test_input_validation.py
@pytest.mark.security
async def test_sql_injection_prevention():
    malicious_data = {
        "va_data": {"insilicova": "'; DROP TABLE users; --"},
        "age_group": "neonate"
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/calibrate", json=malicious_data)
        # Should fail validation, not execute
        assert response.status_code in [400, 422]

@pytest.mark.security
async def test_command_injection_prevention():
    malicious_data = {
        "country": "Mozambique; rm -rf /",
        "age_group": "neonate"
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/calibrate", json=malicious_data)
        # Should sanitize input
        assert response.status_code == 200
```

#### 4.2 Authentication & Authorization (Future)

**Test ID**: ST-002
**Implementation Status**: ⏳ Not Implemented

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| ST-002-01 | No auth header | 401 Unauthorized |
| ST-002-02 | Invalid API key | 401 Unauthorized |
| ST-002-03 | Expired token | 401 Unauthorized |
| ST-002-04 | Rate limit exceeded | 429 Too Many Requests |
| ST-002-05 | CORS validation | Proper headers |

#### 4.3 Data Privacy

**Test ID**: ST-003
**Description**: Ensure no data leakage

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| ST-003-01 | No PII in logs | Logs sanitized |
| ST-003-02 | No data persistence | Temp files deleted |
| ST-003-03 | Error message sanitization | No sensitive info |
| ST-003-04 | Cross-user data isolation | No data mixing |

### 5. Regression Tests

#### 5.1 Backward Compatibility

**Test ID**: RT-001
**Description**: Ensure API changes don't break existing clients

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| RT-001-01 | Old request format support | Still works |
| RT-001-02 | Deprecated field handling | Warning but works |
| RT-001-03 | Version header respect | Correct behavior |

### 6. Smoke Tests

**Test ID**: SM-001
**Description**: Quick validation after deployment

| Test Case | Description | Expected Result | Time |
|-----------|-------------|-----------------|------|
| SM-001-01 | API is accessible | 200 OK | < 1s |
| SM-001-02 | R is available | R ready | < 2s |
| SM-001-03 | Sample data loads | Data available | < 1s |
| SM-001-04 | Basic calibration | Success | < 10s |

```bash
# tests/smoke/smoke_test.sh
#!/bin/bash
# Quick smoke test script

echo "Running smoke tests..."

# Test 1: API health
curl -f http://localhost:8000/ || exit 1
echo "✓ API is healthy"

# Test 2: Example data
curl -f http://localhost:8000/example-data || exit 1
echo "✓ Example data available"

# Test 3: Basic calibration
curl -f -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{"age_group":"neonate","country":"Mozambique"}' || exit 1
echo "✓ Calibration works"

echo "All smoke tests passed!"
```

## Test Data Management

### Test Fixtures

```python
# tests/fixtures/test_data.py
import pytest

@pytest.fixture
def sample_specific_causes():
    return [
        {"ID": "d1", "cause": "Birth asphyxia"},
        {"ID": "d2", "cause": "Neonatal sepsis"},
        {"ID": "d3", "cause": "Prematurity"}
    ]

@pytest.fixture
def sample_binary_matrix():
    return [
        [0, 0, 1, 0, 0, 0],  # sepsis
        [0, 0, 0, 1, 0, 0],  # ipre
        [0, 0, 0, 0, 0, 1]   # prematurity
    ]

@pytest.fixture
def sample_death_counts():
    return {
        "pneumonia": 150,
        "sepsis_meningitis_inf": 300,
        "ipre": 250,
        "prematurity": 200
    }

@pytest.fixture
def mock_r_output():
    return {
        "success": True,
        "uncalibrated": {
            "pneumonia": 0.15,
            "sepsis_meningitis_inf": 0.30
        },
        "calibrated": {
            "insilicova": {
                "pneumonia": 0.12,
                "sepsis_meningitis_inf": 0.35
            }
        }
    }
```

### Mock Services

```python
# tests/mocks/r_service_mock.py
from unittest.mock import MagicMock

def mock_r_execution(success=True):
    mock = MagicMock()
    if success:
        mock.return_value.returncode = 0
        mock.return_value.stdout = '{"success": true, "results": {}}'
    else:
        mock.return_value.returncode = 1
        mock.return_value.stderr = "R execution failed"
    return mock
```

## Test Coverage Requirements

### Coverage Goals
- **Overall**: ≥ 80%
- **Critical paths**: ≥ 95%
- **Error handling**: ≥ 90%
- **New code**: ≥ 85%

### Coverage Reports
```bash
# Generate coverage report
poetry run pytest --cov=app --cov-report=html --cov-report=term

# Coverage by module
poetry run pytest --cov=app.main_direct --cov=app.models --cov=app.services

# Missing lines report
poetry run pytest --cov=app --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install R
      run: |
        sudo apt-get update
        sudo apt-get install -y r-base
        Rscript -e "install.packages(c('jsonlite', 'rstan'))"

    - name: Install dependencies
      run: |
        pip install poetry
        poetry install

    - name: Run tests
      run: |
        poetry run pytest tests/ -v --cov=app

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Test Execution Strategy

### Test Phases

1. **Development Phase**
   - Run unit tests on save
   - Run integration tests before commit
   - Local smoke tests

2. **CI Pipeline**
   - All unit tests
   - Integration tests
   - Security scans
   - Coverage checks

3. **Pre-Production**
   - Full regression suite
   - Performance tests
   - Load tests

4. **Production**
   - Smoke tests after deployment
   - Synthetic monitoring
   - Real user monitoring

### Test Prioritization

**P0 - Critical** (Must pass for deployment)
- Health check endpoint
- Basic calibration with example data
- Error handling
- Data validation

**P1 - High** (Should pass for production)
- All calibration formats
- Data conversion endpoints
- WebSocket functionality
- Performance thresholds

**P2 - Medium** (Good to have)
- Edge cases
- Advanced configurations
- Extensive load testing

**P3 - Low** (Nice to have)
- UI integration tests
- Cross-browser tests
- Localization tests

## Test Maintenance

### Test Review Checklist
- [ ] Tests are independent and isolated
- [ ] Tests use appropriate fixtures
- [ ] Tests have clear assertions
- [ ] Tests handle async operations properly
- [ ] Tests clean up resources
- [ ] Tests are properly categorized
- [ ] Tests have meaningful names
- [ ] Tests cover positive and negative cases

### Test Documentation
Each test should include:
- Test ID for traceability
- Clear description
- Prerequisites
- Test steps (for manual tests)
- Expected results
- Cleanup steps

## Monitoring & Reporting

### Test Metrics
- Test execution time trends
- Failure rate by category
- Flaky test identification
- Coverage trends
- Performance regression detection

### Test Reports
- Daily test execution summary
- Weekly trend analysis
- Sprint test coverage report
- Release test sign-off

---

*Last Updated: 2024-01-18*
*Version: 1.0.0*
*Status: Test Design Phase*