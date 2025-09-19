# VA-Calibration API Test Suite

Comprehensive test suite for the VA-Calibration API following pytest best practices and the test design specifications in `api/api-test.md`.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests for individual endpoints
│   ├── test_health_check.py   # Health endpoint tests (UT-001)
│   ├── test_calibrate.py      # Calibration endpoint tests (UT-002)
│   ├── test_datasets.py       # Dataset endpoints tests (UT-003, UT-004, UT-005)
│   └── test_conversions.py    # Conversion & validation tests (UT-006, UT-007, UT-008, UT-009)
├── integration/                # Integration tests
│   └── test_workflows.py      # End-to-end workflow tests (IT-001, IT-002, IT-003)
├── run_tests.py               # Test runner script
└── README.md                  # This file
```

## Test Categories

### Unit Tests (UT-001 to UT-009)

**Health Check Endpoint (UT-001)**
- ✅ Health check with R available
- ✅ Health check with R unavailable
- ✅ Data files availability check
- ✅ Response time validation
- ✅ JSON structure validation
- ✅ CORS headers validation

**Calibration Endpoint (UT-002)**
- ✅ Calibrate with example data
- ✅ Calibrate with custom specific causes
- ✅ Calibrate with binary matrix
- ✅ Calibrate with death counts
- ✅ Invalid age group validation
- ✅ Invalid country handling
- ✅ Missing required fields validation
- ✅ Malformed JSON handling
- ✅ Empty va_data defaults to example
- ✅ Ensemble calibration
- ✅ Custom MMAT parameters
- ✅ R script timeout handling
- ✅ R script error handling

**Dataset Endpoints (UT-003, UT-004, UT-005)**
- ✅ Example data information retrieval
- ✅ Dataset listing with metadata
- ✅ Dataset preview with statistics
- ✅ Age group filtering
- ✅ Format validation
- ✅ Sample size limits
- ✅ Error handling for invalid datasets

**Conversion & Validation (UT-006, UT-007, UT-008, UT-009)**
- ✅ Cause mapping for neonate and child age groups
- ✅ Unknown cause handling
- ✅ Data validation for different formats
- ✅ Input validation and error reporting
- ✅ Supported configurations retrieval

### Integration Tests (IT-001 to IT-003)

**End-to-End Workflows (IT-001)**
- ✅ Complete sync calibration workflow
- ✅ Data validation → conversion → calibration chain
- ✅ Multiple algorithms ensemble workflow
- ✅ Dataset preview to calibration workflow

**Error Recovery (IT-002)**
- ✅ R script failure recovery
- ✅ Partial data processing handling
- ✅ Timeout simulation and handling
- ✅ Sequential API call resilience

**Data Format Compatibility (IT-003)**
- ✅ Specific → Broad → Calibrate format chain
- ✅ Death counts direct processing
- ✅ Mixed format ensemble handling
- ✅ Cross age group compatibility

## Running Tests

### Prerequisites

Install test dependencies:
```bash
cd api
poetry install
```

### Quick Start

```bash
# Run all tests
python tests/run_tests.py all

# Run only unit tests
python tests/run_tests.py unit

# Run only integration tests
python tests/run_tests.py integration

# Run with coverage
python tests/run_tests.py coverage
```

### Test Runner Options

```bash
# Verbose output
python tests/run_tests.py all -v

# Skip coverage reporting
python tests/run_tests.py unit --no-cov

# Run tests in parallel
python tests/run_tests.py all --parallel

# Quick smoke tests
python tests/run_tests.py smoke

# Security-focused tests
python tests/run_tests.py security

# Performance tests
python tests/run_tests.py performance
```

### Direct pytest Commands

```bash
# Run all tests with coverage
poetry run pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_health_check.py -v

# Run tests matching pattern
poetry run pytest tests/ -k "test_calibrate" -v

# Run integration tests only
poetry run pytest tests/integration -m integration -v

# Generate coverage report
poetry run pytest --cov=app --cov-report=html:htmlcov --cov-report=term-missing
```

## Test Configuration

### Fixtures (conftest.py)

The test suite includes comprehensive fixtures for:

- **HTTP Client**: `async_client` for testing FastAPI endpoints
- **Mock Data**: Sample data for all supported formats
  - `sample_specific_causes` - Specific cause data
  - `sample_binary_matrix` - Binary matrix for broad causes
  - `sample_death_counts` - Death count vectors
  - `child_binary_matrix` - Child age group data
- **Mock R Setup**: `mock_r_ready`, `mock_r_not_ready`
- **Mock Outputs**: Expected R script outputs for success/failure scenarios
- **Performance Data**: Large datasets for performance testing
- **Security Data**: Malicious inputs for security testing
- **Edge Cases**: Boundary conditions and error scenarios

### Mocking Strategy

Tests use comprehensive mocking to:

- **Mock R Script Execution**: All `subprocess.run` calls are mocked
- **Mock File Operations**: `tempfile`, `os.path.exists`, file I/O
- **Mock HTTP Responses**: Using `httpx.AsyncClient` for FastAPI testing
- **Mock Data Files**: R data file existence checks

This ensures tests run quickly and reliably without external dependencies.

## Coverage Requirements

- **Overall Coverage**: ≥ 80%
- **Critical Paths**: ≥ 95% (health check, basic calibration)
- **Error Handling**: ≥ 90%
- **New Code**: ≥ 85%

Current coverage includes:
- All FastAPI endpoints
- Request validation logic
- R script integration points
- Error handling paths
- Data format conversions

## Test Data Management

### Test Categories by Priority

**P0 - Critical** (Must pass for deployment)
- Health check endpoint functionality
- Basic calibration with example data
- Core error handling
- Input validation

**P1 - High** (Should pass for production)
- All calibration data formats
- Data conversion endpoints
- Multiple algorithm support
- Performance baselines

**P2 - Medium** (Good to have)
- Edge case handling
- Advanced configuration options
- Comprehensive error scenarios
- Security validations

**P3 - Low** (Nice to have)
- Unicode handling
- Extensive performance tests
- Cross-browser compatibility (future UI)

## Security Testing

Security tests cover:
- **Input Validation**: SQL injection, command injection prevention
- **Data Sanitization**: XSS prevention, path traversal blocking
- **Error Information**: No sensitive data leakage in error messages
- **Resource Limits**: Large payload handling

## Performance Testing

Performance tests validate:
- **Response Times**: Health check < 100ms, calibration < 30s for typical datasets
- **Concurrency**: Multiple simultaneous requests
- **Large Datasets**: 1000+ death records processing
- **Memory Usage**: No memory leaks during processing

## CI/CD Integration

Tests are designed for continuous integration:

- **Fast Unit Tests**: Run on every commit
- **Integration Tests**: Run on pull requests
- **Full Suite**: Run on main branch changes
- **Coverage Reports**: Generated for all test runs
- **Parallel Execution**: Supported for faster CI runs

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the api directory
cd api
poetry install
```

**R-related Test Failures**
- All R dependencies are mocked in tests
- Real R setup only needed for manual API testing

**Coverage Issues**
```bash
# Generate detailed coverage report
poetry run pytest --cov=app --cov-report=html:htmlcov --cov-fail-under=80
```

**Async Test Issues**
- All async tests use `pytest-asyncio`
- Ensure proper `@pytest.mark.asyncio` decorators

### Test Development

When adding new tests:

1. **Follow naming conventions**: `test_<function_name>_<scenario>`
2. **Use appropriate fixtures**: Leverage existing mock data and setups
3. **Include error cases**: Test both success and failure paths
4. **Add documentation**: Include test IDs and descriptions
5. **Update this README**: Document new test categories

### Performance Benchmarks

Test execution times (approximate):
- **Unit Tests**: ~30 seconds (150+ tests)
- **Integration Tests**: ~15 seconds (25+ tests)
- **Full Suite with Coverage**: ~60 seconds
- **Smoke Tests**: ~5 seconds (critical path only)

## Next Steps

Future enhancements:
- [ ] Add WebSocket testing when async endpoints are implemented
- [ ] Add job status testing for async calibration
- [ ] Add database integration tests when persistence is added
- [ ] Add authentication/authorization tests when security is implemented
- [ ] Add load testing with Locust for production readiness