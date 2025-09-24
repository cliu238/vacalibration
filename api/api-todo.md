# VA-Calibration Implementation Roadmap

## Project Overview
The VA-Calibration project provides an API interface for calibrating computer-coded verbal autopsy (CCVA) algorithm outputs using the vacalibration R package. The system consists of:
- **R Package**: Core calibration logic (vacalibration)
- **API Layer**: FastAPI backend for RESTful interface
- **Frontend**: React-based visualization dashboard (info-visual-scape submodule)

## Current Status Summary (Updated 2025-09-24 - v2.1.0)

### 🎉 Major Milestones Achieved
- ✅ **All 9 core API endpoints implemented** (100% complete)
- ✅ **Async/WebSocket features implemented** (100% complete)
- ✅ **Comprehensive test suite created** (200+ test cases)
- ✅ **Full Pydantic model validation** for all endpoints
- ✅ **Complete R package integration** with error handling
- ✅ **Redis/Celery job queue system** for background processing
- ✅ **Real-time WebSocket streaming** for live updates
- ✅ **Batch processing support** for multiple calibrations
- ✅ **Result caching mechanism** with Redis TTL
- ✅ **API design compliance** - Implementation aligned at ~90%
- ✅ **Security implementation** - API key auth & rate limiting
- ✅ **Service layer architecture** - Fully integrated
- ✅ **Parameter naming alignment** - async_mode → async

### ✅ Completed Components

#### Phase 1: Core Functionality
- [x] **Basic calibration endpoint** - `/calibrate` endpoint implemented in `main_direct.py`
- [x] **Sample data integration** - COMSAMOZ datasets loaded from R package
- [x] **Direct R package execution** - R scripts called via subprocess
- [x] **Health check endpoint** - `/` endpoint with R status verification
- [x] **Example data endpoint** - `/example-data` for testing
- [x] **CORS support** - Enabled for frontend integration
- [x] **Poetry-based dependency management** - Python environment setup
- [x] **API documentation** - Comprehensive API design document
- [x] **Frontend submodule** - React dashboard integrated (info-visual-scape)

#### Infrastructure
- [x] **Docker support** - Dockerfile created for containerization
- [x] **R script integration** - `run_calibration.R` wrapper script
- [x] **Error handling** - Basic exception handling in API
- [x] **Data validation** - Pydantic models for request/response

#### Phase 2: Enhanced Features (Completed 2025-09-19)
- [x] **Full endpoint implementation** - All core endpoints implemented:
  - [x] GET `/datasets` - List available sample datasets (✅ Completed)
  - [x] GET `/datasets/{dataset_id}/preview` - Preview sample data (✅ Completed)
  - [x] POST `/convert/causes` - Convert specific to broad causes (✅ Completed)
  - [x] POST `/validate` - Validate input data format (✅ Completed)
  - [x] GET `/cause-mappings/{age_group}` - Get cause mappings (✅ Completed)
  - [x] GET `/supported-configurations` - Get supported configs (✅ Completed)

### 🚧 In Progress

### 📋 To Be Implemented

#### Phase 2: Enhanced Features (Completed 2025-09-19)
- [x] **Asynchronous processing** - WebSocket and job queue system:
  - [x] WebSocket `/ws/calibrate/{job_id}/logs` - Real-time log streaming (✅ Completed)
  - [x] GET `/calibrate/{job_id}/status` - Job status polling (✅ Completed)
  - [x] POST `/calibrate/async` - Async job creation (✅ Completed)
  - [x] POST `/calibrate/batch` - Batch processing (✅ Completed)
  - [x] Background job processing with Redis/Celery (✅ Completed)
- [x] **Result caching** - Redis-based caching with TTL for sample datasets (✅ Completed)
- [x] **Job management endpoints**:
  - [x] GET `/jobs` - List all jobs with filtering (✅ Completed)
  - [x] GET `/jobs/{job_id}` - Get job status and results (✅ Completed)
  - [x] GET `/jobs/{job_id}/output` - Stream R script output (✅ Completed)
  - [x] POST `/jobs/{job_id}/cancel` - Cancel running job (✅ Completed)
  - [x] DELETE `/jobs/{job_id}` - Delete job (✅ Completed)
- [ ] **Comprehensive validation** - Input data validation beyond basic checks (partially implemented)
- [ ] **OpenVA integration** - Direct integration with openVA outputs (currently users must pre-process)

#### Phase 3: Production Ready (Partially Complete)
- [x] **Authentication system** - API key authentication implemented (✅ Completed 2025-09-24)
- [x] **Rate limiting** - Request throttling per client implemented (✅ Completed 2025-09-24)
- [ ] **Advanced monitoring & logging**:
  - [ ] Structured logging with log levels
  - [ ] Metrics collection (Prometheus/Grafana)
  - [ ] Error tracking (Sentry integration)
- [ ] **Database integration** - Store job history and results
- [ ] **Docker Compose setup** - Multi-container orchestration
- [ ] **Kubernetes deployment** - Production-ready K8s manifests:
  - [ ] Deployment configurations
  - [ ] Service definitions
  - [ ] Ingress rules
  - [ ] ConfigMaps and Secrets
  - [ ] Horizontal Pod Autoscaling

#### Phase 4: Advanced Features (SKIP)
- [ ] **Real-time calibration updates** - Live progress during MCMC iterations
- [ ] **Custom misclassification matrices** - User-provided calibration matrices
- [ ] **Multi-country ensemble calibration** - Cross-country calibration support
- [ ] **GraphQL API option** - Alternative API interface
- [ ] **API versioning** - `/v1/` prefix with version management
- [ ] **Advanced caching strategies** - Redis for distributed caching
- [ ] **Data export formats** - CSV, Excel, JSON export options
- [ ] **Webhook notifications** - Notify clients when jobs complete

## Testing Requirements

### Test Infrastructure Setup (Completed 2025-09-19)
- [x] **Install test framework** (pytest, pytest-asyncio, pytest-cov) - Added to pyproject.toml
- [x] **Set up test directory structure** (`tests/unit`, `tests/integration`, `tests/performance`)
- [x] **Create test fixtures and mock data** - Comprehensive fixtures in conftest.py
- [x] **Configure test coverage reporting** - Coverage configuration included
- [ ] Set up CI/CD test pipeline - Pending deployment configuration

### Unit Tests - All Endpoints (Completed 2025-09-19)
- [x] **UT-001: Health Check Tests** (`GET /`) - 15+ test cases implemented
  - [x] Test with R available
  - [x] Test with R unavailable
  - [x] Test data files availability
  - [x] Performance baseline test
- [x] **UT-002: Calibration Tests** (`POST /calibrate`) - 20+ test cases implemented
  - [x] Test with example data
  - [x] Test with custom specific causes
  - [x] Test with binary matrix
  - [x] Test with death counts
  - [x] Test validation errors
  - [x] Test R script errors
  - [x] Test timeout scenarios
- [x] **UT-003: Example Data Tests** (`GET /example-data`) - Tests implemented
  - [x] Test data structure response
  - [x] Test format specification
  - [x] Test sample counts
- [x] **UT-004: Datasets Tests** (`GET /datasets`) - Tests implemented
- [x] **UT-005: Dataset Preview Tests** (`GET /datasets/{id}/preview`) - Tests implemented
- [x] **UT-006: Convert Causes Tests** (`POST /convert/causes`) - Tests implemented
- [x] **UT-007: Validate Data Tests** (`POST /validate`) - Tests implemented
- [x] **UT-008: Cause Mappings Tests** (`GET /cause-mappings/{age_group}`) - Tests implemented
- [x] **UT-009: Supported Configurations Tests** (`GET /supported-configurations`) - Tests implemented
- [ ] **UT-010: Job Status Tests** (`GET /calibrate/{job_id}/status`)
- [ ] **UT-011: WebSocket Tests** (`WS /calibrate/{job_id}/logs`)

### Integration Tests (Completed 2025-09-19)
- [x] **IT-001: End-to-End Workflows** - 15+ test cases implemented
  - [x] Complete sync calibration workflow
  - [ ] Complete async calibration workflow (pending async implementation)
  - [x] Multi-step validation → conversion → calibration
  - [x] Ensemble calibration workflow
- [x] **IT-002: Error Recovery** - Tests implemented
  - [x] R script failure recovery
  - [x] Timeout and retry mechanisms
  - [x] Partial data handling
- [x] **IT-003: Data Format Compatibility** - Tests implemented
  - [x] All format conversions
  - [x] Mixed format ensemble

### Performance Tests
- [ ] **PT-001: Load Testing**
  - [ ] Response time benchmarks (small/medium/large datasets)
  - [ ] Concurrent user testing (100+ users)
  - [ ] Requests per second baseline
  - [ ] Memory usage profiling
- [ ] **PT-002: Stress Testing**
  - [ ] 500 concurrent calibrations
  - [ ] Large dataset processing (10K+ deaths)
  - [ ] Memory leak detection
  - [ ] R process cleanup verification

### Security Tests
- [ ] **ST-001: Input Validation Security**
  - [ ] SQL injection prevention
  - [ ] Command injection prevention
  - [ ] Path traversal prevention
  - [ ] JSON bomb protection
- [ ] **ST-003: Data Privacy**
  - [ ] No PII in logs
  - [ ] Temp file cleanup
  - [ ] Error message sanitization

### Test Automation
- [ ] Create pytest fixtures for common test data
- [ ] Implement mock R service for testing
- [ ] Set up automated test execution in CI
- [ ] Configure code coverage thresholds (≥80%)
- [ ] Create smoke test suite for deployment validation
- [ ] Set up performance test automation with Locust

### Test Documentation
- [ ] Document test execution procedures
- [ ] Create test data preparation guide
- [ ] Write test troubleshooting guide
- [ ] Maintain test case traceability matrix

## Documentation Requirements

### Completed
- [x] API design document
- [x] Basic README with setup instructions
- [x] How to generate OpenVA output guide (✅ Completed 2025-09-24)

### To Be Completed
- [ ] OpenAPI/Swagger specification
- [ ] Interactive API explorer (Swagger UI)
- [ ] Code examples in multiple languages (Python, R, JavaScript)
- [ ] User guides:
  - [ ] Getting started tutorial
  - [ ] OpenVA integration guide
  - [ ] Data preparation guidelines
  - [ ] Interpretation of results
- [ ] Developer documentation:
  - [ ] Architecture overview
  - [ ] Contributing guide
  - [ ] API client SDKs

## Implementation Priorities

### Immediate (Sprint 1)
1. **Complete core API endpoints** - Implement remaining GET endpoints
2. **Add async support** - Basic job queue for long-running calibrations
3. **Enhance error handling** - Better error messages and validation

### Short-term (Sprint 2-3)
1. **Add authentication** - Basic API key authentication
2. **Implement caching** - Cache results for common requests
3. **Add monitoring** - Basic logging and metrics
4. **Write tests** - Core unit and integration tests

### Medium-term (Sprint 4-6)
1. **Production deployment** - Docker Compose and basic K8s setup
2. **Performance optimization** - Connection pooling, caching
3. **Complete documentation** - OpenAPI spec and user guides
4. **Frontend enhancements** - Full integration with all endpoints

### Long-term
1. **Advanced features** - GraphQL, webhooks, custom matrices
2. **Scalability** - Horizontal scaling, distributed processing
3. **Multi-region support** - CDN and geo-distributed deployment
4. **Enterprise features** - SSO, audit logs, compliance

## Technical Debt

### Current Issues
- ~~No test coverage~~ ✅ 200+ tests implemented
- Limited error handling in R scripts (partially addressed)
- No database for job persistence (using Redis for now)
- ~~Synchronous processing only~~ ✅ Async processing implemented
- ~~No request validation middleware~~ ✅ Pydantic validation implemented
- Missing OpenAPI documentation
- No CI/CD pipeline

### Refactoring Needs
- ~~Separate business logic from API routes~~ ✅ Service layer implemented
- ~~Create service layer for R interaction~~ ✅ CalibrationService created
- Implement dependency injection (partially done)
- Add configuration management (partially done)
- Standardize error responses (partially done)

## Success Metrics

### API Performance
- Response time < 2s for small datasets
- Support 100+ concurrent users
- 99.9% uptime SLA
- < 1% error rate

### User Experience
- Complete calibration in < 30s for typical datasets
- Real-time progress feedback
- Clear error messages
- Comprehensive documentation

### Development
- 80%+ test coverage
- Automated deployment pipeline
- < 1 day from commit to production
- Active monitoring and alerting

## Next Steps

1. **Review and prioritize** this roadmap with stakeholders
2. **Set up project board** with GitHub Issues/Projects
3. **Define sprint goals** for next 2-3 sprints
4. **Recruit contributors** if needed for parallel development
5. **Establish CI/CD pipeline** for automated testing and deployment

---

*Last Updated: 2025-09-24*
*Status: Core Implementation Complete with Security*
*Version: 2.1.0*
*Endpoints Implemented: 9/9 (100%)*
*Test Coverage: 200+ test cases*
*API Design Alignment: ~90%*
*Security Features: API Key Auth + Rate Limiting*